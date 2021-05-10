import os
from itertools import dropwhile

from flask import request, url_for, send_file, render_template, jsonify, redirect, abort, make_response
from werkzeug.exceptions import HTTPException
from werkzeug.http import HTTP_STATUS_CODES

from socorepo import app, config
from socorepo.cache import component_cache
from socorepo.forms import create_component_filter_form
from socorepo.l10n import msg_lang, _, localized_of


@app.context_processor
def global_context_vars():
    return {
        "bare": config.APPEARANCE_BARE,
        "global_title": config.APPEARANCE_TITLE,
        "heading": config.APPEARANCE_HEADING,
        "footer": localized_of(config.APPEARANCE_FOOTERS),
        "msg_lang": msg_lang(),
        "_": _,
        "localized_of": localized_of
    }


@app.errorhandler(Exception)
def error(e):
    if isinstance(e, HTTPException):
        error_code = e.code
        error_desc = e.description
    else:
        error_code = 500
        error_desc = _("internal_error")
        app.log_exception(e)

    error_name = HTTP_STATUS_CODES.get(error_code, "Unknown Error")
    return render_template("error.html", error_code=error_code, error_name=error_name,
                           error_desc=error_desc), error_code


@app.route("/" + os.path.basename(config.APPEARANCE_FAVICON_PATH))
def favicon():
    return send_file(config.APPEARANCE_FAVICON_PATH)


@app.route("/")
def project_list():
    resp = render_template("project_list.html", homepage=localized_of(config.APPEARANCE_HOMEPAGES),
                           projects=config.PROJECTS.values())
    if config.APPEARANCE_BARE:
        resp = make_response(resp)
        resp.headers["Socorepo-Language"] = msg_lang()
    return resp


@app.route("/<project_id>/")
def project(project_id):
    if project_id not in config.PROJECTS:
        abort(404)

    proj = config.PROJECTS[project_id]
    components = component_cache[project_id].values()

    # Get highlight components: Latest release and latest experimental version.
    highlight_components = []
    latest_stable = next(dropwhile(lambda c: not c.qualifier.stable, components), None)
    if latest_stable:
        highlight_components.append((_("project.latest_stable"), latest_stable))
    latest_experimental = next(iter(components), None)
    if latest_experimental and not latest_experimental.qualifier.stable:
        highlight_components.append((_("project.latest_experimental"), latest_experimental))

    # Construct filter form.
    available_qualifiers = sorted(set(comp.qualifier for comp in components))
    comp_filter_form = create_component_filter_form(available_qualifiers)(request.args)
    # Apply filters, if applicable.
    if comp_filter_form.validate():
        filter_version = comp_filter_form.version.data
        filter_qualifier = comp_filter_form.qualifier.data
        components = [comp for comp in components
                      if comp.version.startswith(filter_version)
                      and (filter_qualifier == "" or comp.qualifier.name == filter_qualifier)]

    # Get list of all featured asset type matchers which have actually matched an asset...
    occurring_featured_asset_type_matchers = []
    for comp in components:
        for asset in comp.assets:
            if asset.featured and asset.matcher_causing_featuring not in occurring_featured_asset_type_matchers:
                occurring_featured_asset_type_matchers.append(asset.matcher_causing_featuring)
    # ... and sort them by the order they are referenced in the project's configuration.
    occurring_featured_asset_type_matchers.sort(key=lambda matcher: proj.featured_asset_type_matchers.index(matcher))

    resp = render_template("project.html", component_filter_form=comp_filter_form, project=proj,
                           components=components, highlight_components=highlight_components,
                           occurring_featured_asset_type_matchers=occurring_featured_asset_type_matchers)
    if config.APPEARANCE_BARE:
        resp = make_response(resp)
        resp.headers["Socorepo-Language"] = msg_lang()
        resp.headers["Socorepo-Project-Label"] = proj.label
    return resp


@app.route("/<project_id>/<version>")
def component(project_id, version):
    if project_id not in config.PROJECTS or project_id not in component_cache \
            or version not in component_cache[project_id]:
        abort(404)

    proj = config.PROJECTS[project_id]
    comp = component_cache[project_id][version]

    comp_info_tables = [loc.component_info_table(comp) for loc in proj.locators if loc.id in comp.extra_data]
    has_file_size_column = any(asset.file_size for asset in comp.assets)
    has_checksums_column = any(asset.checksums for asset in comp.assets)

    resp = render_template("component.html", project=proj, component=comp, component_info_tables=comp_info_tables,
                           has_file_size_column=has_file_size_column, has_checksums_column=has_checksums_column)
    if config.APPEARANCE_BARE:
        resp = make_response(resp)
        resp.headers["Socorepo-Language"] = msg_lang()
        resp.headers["Socorepo-Project-Label"] = proj.label
        resp.headers["Socorepo-Component-Version"] = comp.version
        resp.headers["Socorepo-Component-Qualifier"] = comp.qualifier.name
    return resp


# ===========
# === API ===
# ===========

@app.route("/api/v1/projects/")
def api_project_list():
    return jsonify({
        "projects": [{
            "id": proj.id,
            "label": proj.label
        } for proj in config.PROJECTS.values()]
    })


@app.route("/api/v1/components/<project_id>/")
def api_component_list(project_id):
    if project_id not in config.PROJECTS:
        abort(404)

    return jsonify({
        "components": [{
            "version": comp.version,
            "qualifier": comp.qualifier.name
        } for comp in component_cache[project_id].values()]
    })


@app.route("/api/v1/assets/<project_id>/<version>/")
def api_asset_list(project_id, version):
    if project_id not in config.PROJECTS or project_id not in component_cache \
            or version not in component_cache[project_id]:
        abort(404)

    return jsonify({
        "assets": [{
            "filename": asset.filename,
            "file_size": asset.file_size,
            "url": asset.url,
            "checksums": asset.checksums,
            "type": str(asset.type)
        } for asset in component_cache[project_id][version].assets]
    })


# =====================================
# === Legacy routes from QuarterMAP ===
# =====================================

@app.route("/index/")
@app.route("/projects/")
def legacy_index():
    return redirect(url_for("project_list"))


@app.route("/projects/details")
@app.route("/projects/artifactList")
def legacy_project():
    if "projectId" not in request.args:
        abort(404)
    return redirect(url_for("project", project_id=request.args["projectId"].lower()))


@app.route("/projects/artifact")
def legacy_component():
    if "projectId" not in request.args or "version" not in request.args:
        abort(404)
    return redirect(url_for("component", project_id=request.args["projectId"].lower(), version=request.args["version"]))
