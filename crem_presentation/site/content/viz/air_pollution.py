# -*- coding: utf-8 -*- #
from bokeh.embed import components
from bokeh.models import TextInput, CustomJS

from jinja2 import Template

from .charts import get_national_scenario_line_plot
from .scenarios import scenarios
from .utils import get_js_array, env


def _get():
    ap_plot, ap_line_renderers = get_national_scenario_line_plot(
        parameter='NOX_emi',
        y_ticks=[25, 35, 45],
        y_label='NOx emissions',
        plot_width=400,
    )
    co2_plot, co2_line_renderers = get_national_scenario_line_plot(
        parameter='CO2_emi',
        y_ticks=[7000, 10000, 13000, 16000],
        y_label='CO₂ emissions',
        plot_width=400,
    )
    prefixed_line_renderers = {}
    for key in scenarios:
        prefixed_line_renderers['ap_%s' % key] = ap_line_renderers[key]
        prefixed_line_renderers['co2_%s' % key] = co2_line_renderers[key]

    line_array = get_js_array(prefixed_line_renderers.keys())
    print(line_array)
    code = '''
        var lines = %s,
            highlight = cb_obj.get('value').split(',');
        Bokeh.$.each(lines, function(key, line) {
            glyph = line.get('glyph');
            glyph.set('line_alpha', 0.1);
        });
        Bokeh.$.each(highlight, function(i, key) {
            function set_alpha(line) {
                glyph = line.get('glyph');
                glyph.set('line_alpha', 0.8);
            }
            set_alpha(lines['ap_' + key]);
            set_alpha(lines['co2_' + key]);
        });
    ''' % line_array

    callback = CustomJS(code=code, args=prefixed_line_renderers)
    text = TextInput(callback=callback)
    return (co2_plot, ap_plot, text)


def render_1():
    co2_plot, ap_plot, text = _get()
    template = env.get_template('viz/co2_plot_ap_plot_with_selectors.html')
    script, div = components(dict(co2_plot=co2_plot, ap_plot=ap_plot, text=text), wrap_plot_info=False)
    return template.render(plot_script=script, plot_div=div)


def render_2():
    return 'with NH3'
