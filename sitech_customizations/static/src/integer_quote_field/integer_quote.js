/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { integerField, IntegerField } from "@web/views/fields/integer/integer_field";
import { useService } from "@web/core/utils/hooks";


export class IntegerQuote extends IntegerField {
    static props= {
        ...IntegerField.props,
        quoteAction: { type: String },
    }
    setup(){
        super.setup()
        this.action = useService("action");
        this.orm = useService("orm")
    }
    async openQuoteAction() {
        if (this.props.quoteAction){
            const result = await this.orm.call(
                    "sales.target.line",
                    this.props.quoteAction,
                    [[this.props.record.data.id]]
                );
            this.action.doAction({
                type: result.type,
                name: result.name,
                target: result.target,
                domain: result.domain,
                res_model: result.res_model,
                views: [[false, result.view_mode]],
            });
        }
    }
}

IntegerQuote.template = "sitech_customizations.IntegerQuote"
IntegerQuote.supportedTypes = ["integer"]


export const integerQuoteComp = {
    ...integerField,
    component: IntegerQuote,
    displayName: _t("Quote Integer"),
    extractProps ({ options }) {
        return {
            ...integerField.extractProps(...arguments),
            quoteAction: options.quote_action,
        }
    }
};
registry.category("fields").add("integer_quote", integerQuoteComp);

