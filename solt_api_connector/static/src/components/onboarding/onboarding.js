import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

class ConnectorOnboardingWidget extends Component {
    static template = "solt_api_connector.Onboarding";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ steps: [], closed: true, completed: false, panelId: false });
        onWillStart(() => this.load());
    }

    get resId() {
        return this.props.record.resId;
    }

    get requiredSteps() {
        return this.state.steps.filter((step) => !step.optional);
    }

    get optionalSteps() {
        return this.state.steps.filter((step) => step.optional);
    }

    imageUrl(step) {
        return `/web/image/onboarding.onboarding.step/${step.id}/step_image`;
    }

    async load() {
        if (!this.resId) {
            return;
        }
        const data = await this.orm.call("solt.api.connector", "get_onboarding_data", [[this.resId]]);
        Object.assign(this.state, data);
    }

    async safeLoad() {
        // The step action may replace the form (and destroy this widget): do not reload then.
        try {
            await this.load();
        } catch (error) {
            if (!String(error && error.message).includes("destroyed")) {
                throw error;
            }
        }
    }

    async onStepClick(step) {
        if (step.blocked && !step.done) {
            return;
        }
        const action = await this.orm.call("onboarding.onboarding.step", step.action, [], {
            context: { connector_id: this.resId },
        });
        await this.action.doAction(action, { onClose: () => this.safeLoad() });
        await this.safeLoad();
    }

    async onClose() {
        await this.orm.call("onboarding.onboarding", "action_toggle_visibility", [[this.state.panelId]]);
        this.state.closed = true;
    }

    async onReopen() {
        await this.orm.call("onboarding.onboarding", "action_toggle_visibility", [[this.state.panelId]]);
        this.state.closed = false;
    }
}

registry.category("view_widgets").add("solt_connector_onboarding", {
    component: ConnectorOnboardingWidget,
});
