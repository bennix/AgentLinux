#include <fcitx/addonfactory.h>
#include <fcitx/addonmanager.h>
#include <fcitx/candidatelist.h>
#include <fcitx/inputcontext.h>
#include <fcitx/inputmethodengine.h>
#include <fcitx/inputpanel.h>
#include <fcitx/instance.h>
#include <gio/gio.h>
#include <json-c/json.h>
#include <enchant.h>
#include <algorithm>
#include <functional>
#include <filesystem>
#include <memory>

using namespace fcitx;
using Json = std::unique_ptr<json_object, decltype(&json_object_put)>;
static json_object *field(json_object *o, const char *name) {
    return json_object_object_get(o, name);
}
static std::string stringField(json_object *o, const char *name) {
    auto value = json_object_get_string(field(o, name));
    return value ? value : "";
}
class Choice final : public CandidateWord {
public:
    Choice(Text text, std::function<void(InputContext *)> select)
        : CandidateWord(std::move(text)), callback(std::move(select)) {}
    void select(InputContext *ic) const override { callback(ic); }
private:
    std::function<void(InputContext *)> callback;
};

class MyIME final : public InputMethodEngine {
    GSubprocess *host = nullptr;
    GDataInputStream *output = nullptr;
    EnchantBroker *broker = enchant_broker_init();
    EnchantDict *english = broker ? enchant_broker_request_dict(broker, "en_US") : nullptr;
    std::shared_ptr<CommonCandidateList> list;
    std::string raw;
    bool suggesting = false, navigated = false, expanded = false, shiftDown = false, englishMode = false;
    int normalSize = 5;

    void clearComposition(InputContext *ic) {
        raw.clear();
        list.reset();
        suggesting = false;
        ic->inputPanel().reset();
        ic->updatePreedit();
        ic->updateUserInterface(UserInterfaceComponent::InputPanel);
    }

    void stop() {
        if (host) g_output_stream_close(g_subprocess_get_stdin_pipe(host), nullptr, nullptr);
        g_clear_object(&output);
        g_clear_object(&host);
    }
    std::filesystem::file_time_type loadedMarker{};
    bool start() {
        std::error_code error;
        auto marker = std::filesystem::last_write_time(
            std::filesystem::path(g_get_user_data_dir()) / "myime" / "reload", error);
        if (host && marker != loadedMarker && raw.empty()) stop();
        if (host) return true;
        loadedMarker = marker;
        host = g_subprocess_new(GSubprocessFlags(G_SUBPROCESS_FLAGS_STDIN_PIPE | G_SUBPROCESS_FLAGS_STDOUT_PIPE),
                                nullptr, "/usr/lib/myime/MyIMEHost", nullptr);
        if (!host) return false;
        output = g_data_input_stream_new(g_subprocess_get_stdout_pipe(host));
        return true;
    }
    bool request(InputContext *ic, const char *op, std::string text = {}, int index = -1) {
        if (!start()) return false;
        Json q(json_object_new_object(), json_object_put);
        json_object_object_add(q.get(), "op", json_object_new_string(op));
        json_object_object_add(q.get(), "text", json_object_new_string(text.c_str()));
        json_object_object_add(q.get(), "index", json_object_new_int(index));
        std::string spelling = raw + text;
        if (std::string(op) == "back" && !spelling.empty()) spelling.pop_back();
        if (english && (std::string(op) == "append" || std::string(op) == "back") && spelling.size() >= 2 &&
            spelling.find_first_not_of("abcdefghijklmnopqrstuvwxyz") == std::string::npos) {
            auto words = json_object_new_array();
            if (enchant_dict_check(english, spelling.c_str(), -1) == 0)
                json_object_array_add(words, json_object_new_string(spelling.c_str()));
            else {
                size_t count = 0;
                char **items = enchant_dict_suggest(english, spelling.c_str(), -1, &count);
                for (size_t i = 0; i < std::min<size_t>(2, count); ++i)
                    json_object_array_add(words, json_object_new_string(items[i]));
                if (items) enchant_dict_free_string_list(english, items);
            }
            json_object_object_add(q.get(), "english", words);
        }
        std::string line = std::string(json_object_to_json_string(q.get())) + "\n";
        if (!g_output_stream_write_all(g_subprocess_get_stdin_pipe(host), line.data(), line.size(), nullptr, nullptr, nullptr)) {
            stop(); return false;
        }
        gchar *response = g_data_input_stream_read_line(output, nullptr, nullptr, nullptr);
        if (!response) { stop(); return false; }
        Json result(json_tokener_parse(response), json_object_put);
        g_free(response);
        if (!result || !field(result.get(),"words")) return false;
        auto commit = stringField(result.get(),"commit");
        if (!commit.empty()) ic->commitString(commit);
        raw = stringField(result.get(),"raw");
        suggesting = json_object_get_boolean(field(result.get(),"suggesting"));
        const auto preedit = stringField(result.get(),"preedit");
        ic->inputPanel().reset();
        Text marked(preedit, TextFormatFlag::Underline);
        marked.setCursor(preedit.size());
        if (ic->capabilityFlags().test(CapabilityFlag::Preedit))
            ic->inputPanel().setClientPreedit(marked);
        else ic->inputPanel().setPreedit(marked);
        list.reset();
        auto words = field(result.get(),"words");
        if (json_object_array_length(words)) {
            ic->inputPanel().setCandidateList(std::make_unique<CommonCandidateList>());
            list = std::static_pointer_cast<CommonCandidateList>(ic->inputPanel().candidateList());
            normalSize = json_object_get_int(field(result.get(),"pageSize"));
            list->setPageSize(expanded ? 36 : normalSize);
            list->setLayoutHint(json_object_get_boolean(field(result.get(),"vertical")) ?
                CandidateLayoutHint::Vertical : CandidateLayoutHint::Horizontal);
            list->setCursorPositionAfterPaging(CursorPositionAfterPaging::ResetToFirst);
            for (size_t i=0; i<json_object_array_length(words); ++i) {
                auto word = json_object_get_string(json_object_array_get_idx(words,i));
                list->append<Choice>(Text(word), [this,i](InputContext *ctx) { choose(ctx,i); });
            }
            list->setGlobalCursorIndex(0);

        }
        ic->updatePreedit();
        ic->updateUserInterface(UserInterfaceComponent::InputPanel);
        return true;
    }
    void choose(InputContext *ic, int i) {
        auto selectedList = list;
        navigated = expanded = false;
        request(ic,"select",{},i);
    }
public:
    void activate(const InputMethodEntry &, InputContextEvent &) override { start(); }
    ~MyIME() override {
        stop();
        if (english) enchant_broker_free_dict(broker,english);
        if (broker) enchant_broker_free(broker);
    }
    void reset(const InputMethodEntry &, InputContextEvent &event) override {
        expanded = navigated = shiftDown = false;
        if (host) request(event.inputContext(),"reset");
    }
    void deactivate(const InputMethodEntry &entry, InputContextEvent &e) override { reset(entry,e); englishMode=false; }
    void keyEvent(const InputMethodEntry &, KeyEvent &e) override {
        const auto key=e.key();
        auto sym=key.sym();
        auto ic=e.inputContext();
        if (sym==FcitxKey_Shift_L || sym==FcitxKey_Shift_R) {
            if (!e.isRelease()) shiftDown=true;
            else if (shiftDown) {
                shiftDown=false;
                if (!raw.empty()) request(ic,"literal");
                else if (suggesting) request(ic,"reset");
                englishMode=!englishMode;
            }
            return;
        }
        if(e.isRelease()) return;
        shiftDown=false;
        if (englishMode || key.states().test(KeyState::Ctrl) || key.states().test(KeyState::Alt) || key.states().test(KeyState::Super)) return;
        bool active=list || !raw.empty() || suggesting;
        bool handled=true;
        if(sym>=FcitxKey_a && sym<=FcitxKey_z)
            { navigated=expanded=false; handled=request(ic,"append",std::string(1,char(sym))); }
        else if(sym==FcitxKey_apostrophe && !raw.empty()) handled=request(ic,"append","'");
        else if(sym==FcitxKey_BackSpace && active) handled=request(ic,raw.empty()?"reset":"back");
        else if(sym==FcitxKey_Escape && active) {
            expanded = navigated = false;
            if (!request(ic,"reset")) clearComposition(ic);
        }
        else if((sym==FcitxKey_Return || sym==FcitxKey_KP_Enter) && active) {
            if(suggesting) request(ic,"reset");
            else if(navigated && list) choose(ic,list->globalCursorIndex());
            else request(ic,"literal");
        } else if(list && sym==FcitxKey_space) choose(ic,list->globalCursorIndex());
        else if(list && sym>=FcitxKey_1 && sym<=FcitxKey_9) {
            int i=sym-FcitxKey_1;
            int row=expanded ? (list->cursorIndex()/6)*6 : 0;
            if ((!expanded || i<6) && row+i<list->size()) choose(ic,list->currentPage()*list->pageSize()+row+i);
        } else if(list && (sym==FcitxKey_Left || sym==FcitxKey_Right || sym==FcitxKey_Down || sym==FcitxKey_Up)) {
            navigated=true;
            const bool shift = key.states().test(KeyState::Shift);
            if(shift && sym==FcitxKey_Down && !expanded) {expanded=true; list->setPageSize(36);}
            else if(shift && sym==FcitxKey_Up && expanded) {expanded=false; list->setPageSize(normalSize);}
            else {
                const int rowStep = expanded && list->layoutHint() != CandidateLayoutHint::Vertical ? 6 : 1;
                int delta=sym==FcitxKey_Right?1:sym==FcitxKey_Left?-1:sym==FcitxKey_Down?rowStep:-rowStep;
                list->setGlobalCursorIndex(std::clamp(list->globalCursorIndex()+delta,0,list->totalSize()-1));
            }
            ic->updateUserInterface(UserInterfaceComponent::InputPanel);
        } else if(list && (sym==FcitxKey_Page_Up || sym==FcitxKey_Page_Down || sym==FcitxKey_minus || sym==FcitxKey_equal || sym==FcitxKey_comma || sym==FcitxKey_period)) {
            navigated=true;
            if(sym==FcitxKey_Page_Up || sym==FcitxKey_minus || sym==FcitxKey_comma) list->prev();
            else list->next();
            ic->updateUserInterface(UserInterfaceComponent::InputPanel);
        } else {
            if(!raw.empty() && sym>=0x21 && sym<=0x7e) {
                if (sym>=FcitxKey_A && sym<=FcitxKey_Z) {request(ic,"literal"); return;}
                if(list) choose(ic,list->globalCursorIndex()); else request(ic,"literal");
                const std::string punct="?!;:()";
                const char *zh[]={"？","！","；","：","（","）"};
                auto n=punct.find(char(sym));
                ic->commitString(n==std::string::npos?std::string(1,char(sym)):zh[n]);
                request(ic,"reset");
            } else { if(suggesting || sym==FcitxKey_space) { if(host) request(ic,"reset"); } handled=false; }
        }
        if(handled) e.filterAndAccept();
    }
};
class Factory final : public AddonFactory {
    AddonInstance *create(AddonManager *) override { return new MyIME; }
};
FCITX_ADDON_FACTORY(Factory)
