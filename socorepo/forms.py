from flask_wtf import FlaskForm
from wtforms import TextField, SelectField, SubmitField

from socorepo import config


def create_component_filter_form(available_qualifiers):
    default_qualifier = config.DEFAULT_VERSION_QUALIFIER

    class ComponentFilterForm(FlaskForm):
        version = TextField("Version (starts with):")
        qualifier = SelectField("Qualifier:",
                                choices=[("", "Any")] + [(q.name, q.name) for q in available_qualifiers],
                                default=default_qualifier.name if default_qualifier in available_qualifiers else "")
        filter = SubmitField("Filter")

    return ComponentFilterForm
