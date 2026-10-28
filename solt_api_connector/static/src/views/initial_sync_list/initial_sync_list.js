import { onMounted, onWillUnmount } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

const RUNNING_STATES = ["scheduled", "running"];
const REFRESH_DELAY = 5000;

/**
 * List of the initial import/export actions. The imports and exports run in the
 * background (cron), so while one is scheduled or running the list reloads itself
 * and tells the user when it finishes. A reload keeps the breadcrumb of the page.
 */
export class InitialSyncListController extends ListController {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.timer = null;
        this.busy = false;
        onMounted(() => {
            this.timer = setInterval(() => this.autoRefresh(), REFRESH_DELAY);
        });
        onWillUnmount(() => clearInterval(this.timer));
    }

    syncState(record) {
        const data = record.data;
        return data.use_for_initial_import ? data.importing_state : data.exporting_state;
    }

    snapshot() {
        const states = new Map();
        for (const record of this.model.root.records) {
            states.set(record.resId, { name: record.data.name, state: this.syncState(record) });
        }
        return states;
    }

    async autoRefresh() {
        if (this.busy || document.hidden) {
            return;
        }
        const before = this.snapshot();
        if (![...before.values()].some(({ state }) => RUNNING_STATES.includes(state))) {
            return;
        }
        this.busy = true;
        try {
            await this.model.load();
            for (const record of this.model.root.records) {
                const previous = before.get(record.resId);
                const state = this.syncState(record);
                if (previous && RUNNING_STATES.includes(previous.state) && !RUNNING_STATES.includes(state)) {
                    this.notifyFinished(record.data.name, state);
                }
            }
        } catch {
            // The list may have been closed while reloading: nothing to do.
        } finally {
            this.busy = false;
        }
    }

    notifyFinished(name, state) {
        if (state === "error") {
            this.notification.add(_t("%(name)s finished with an error.", { name }), { type: "danger" });
        } else {
            this.notification.add(_t("%(name)s completed.", { name }), { type: "success" });
        }
    }
}

registry.category("views").add("solt_initial_sync_list", {
    ...listView,
    Controller: InitialSyncListController,
});
