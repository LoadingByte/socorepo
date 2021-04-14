from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField

from socorepo import config
from socorepo.l10n import _


def create_component_filter_form(available_qualifiers):
    default_qualifier = config.DEFAULT_VERSION_QUALIFIER

    class ComponentFilterForm(FlaskForm):
        version = StringField(_("project.filter_version"))
        qualifier = SelectField(_("project.filter_qualifier"),
                                choices=[("", "Any")] + [(q.name, q.name) for q in available_qualifiers],
                                default=default_qualifier.name if default_qualifier in available_qualifiers else "")
        filter = SubmitField(_("project.filter"))

    return ComponentFilterForm
