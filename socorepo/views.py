import os
from itertools import dropwhile

from flask import request, url_for, send_file, render_template, jsonify, redirect, abort
from werkzeug.exceptions import HTTPException
from werkzeug.http import HTTP_STATUS_CODES

from socorepo import app, config
from socorepo.cache import component_cache
from socorepo.forms import create_component_filter_form


@app.context_processor
def global_context_vars():
    return {
        "global_title": config.APPEARANCE_TITLE,
        "heading": config.APPEARANCE_HEADING,
        "footer": config.APPEARANCE_FOOTER
    }


@app.errorhandler(Exception)
def error(e):
    if isinstance(e, HTTPException):
        error_code = e.code
        error_desc = e.description
    else:
        error_code = 500
        error_desc = "The server encountered an internal error and was unable to complete your request."
        app.log_exception(e)

    error_name = HTTP_STATUS_CODES.get(error_code, "Unknown Error")
    return render_template("error.html", error_code=error_code, error_name=error_name,
                           error_desc=error_desc), error_code


@app.route("/" + os.path.basename(config.APPEARANCE_FAVICON_PATH))
def favicon():
    return send_file(config.APPEARANCE_FAVICON_PATH)


@app.route("/")
def project_list():
    return render_template("project_list.html", homepage=config.APPEARANCE_HOMEPAGE, projects=config.PROJECTS.values())


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
        highlight_components.append(("Latest stable (recommended)", latest_stable))
    latest_experimental = next(iter(components), None)
    if latest_experimental and not latest_experimental.qualifier.stable:
        label = "Latest experimental"
        highlight_components.append((label, latest_experimental))

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
    occurring_featured_asset_type_matchers.sort(key=lambda clfs: proj.featured_asset_type_matchers.index(clfs))

    return render_template("project.html", component_filter_form=comp_filter_form, project=proj,
                           components=components, highlight_components=highlight_components,
                           occurring_featured_asset_type_matchers=occurring_featured_asset_type_matchers)


@app.route("/<project_id>/<version>")
def component(project_id, version):
    if project_id not in config.PROJECTS or project_id not in component_cache \
            or version not in component_cache[project_id]:
        abort(404)

    proj = config.PROJECTS[project_id]
    comp = component_cache[project_id][version]

    comp_info_table = proj.locator.component_info_table(comp)
    has_file_size_column = any(asset.file_size for asset in comp.assets)
    has_checksums_column = any(asset.checksums for asset in comp.assets)

    return render_template("component.html", project=proj, component=comp, component_info_table=comp_info_table,
                           has_file_size_column=has_file_size_column, has_checksums_column=has_checksums_column)


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
