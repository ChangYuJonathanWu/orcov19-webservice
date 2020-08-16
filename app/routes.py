from collections import OrderedDict
from json import JSONDecodeError
import grequests
from flask import render_template, flash, redirect, url_for, request, abort, Response
from app import app, db, cache
from app.forms import LoginForm, AdminForm
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from app.models import User, ProductionData, StagingData
from sqlalchemy import text
from app import scraper
from datetime import datetime

import requests
import logging
import json
import time

COUNTIES = [
            "baker",
            "benton",
            "clackamas",
            "clatsop",
            "columbia",
            "coos",
            "crook",
            "curry",
            "deschutes",
            "douglas",
            "gilliam",
            "grant",
            "harney",
            "hood river",
            "jackson",
            "jefferson",
            "josephine",
            "klamath",
            "lake",
            "lane",
            "lincoln",
            "linn",
            "malheur",
            "marion",
            "morrow",
            "multnomah",
            "polk",
            "sherman",
            "tillamook",
            "umatilla",
            "union",
            "wallowa",
            "wasco",
            "washington",
            "wheeler",
            "yamhill"]


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('admin'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('admin')
        return redirect(next_page)
    return render_template('login.html', title='Login', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/', methods=['GET', 'POST'])
@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    form = AdminForm()
    staging_raw = StagingData.query.order_by(text('-id')).first()
    production_raw = ProductionData.query.order_by(text('-id')).first()
    staging = "{}" if staging_raw is None else staging_raw.data
    production = "{}" if production_raw is None else production_raw.data
    default = type('', (object,), {'data': staging})
    form = AdminForm(obj=default)
    if form.validate_on_submit():
        if form.submit_new.data:
            new_data = form.data.data
            try:
                json.loads(new_data)
            except JSONDecodeError as ex:
                flash('Invalid JSON. data not staged. ' + str(ex))
                return render_template('admin.html', title='Admin', form=form, staging=staging, production=production)
            else:
                staging_json = str(form.data.data)
                db.session.add(StagingData(data=staging_json))
                flash('Staging updated')

        if form.promote.data:
            try:
                json.loads(staging)
            except JSONDecodeError as ex:
                flash('Invalid JSON in staging. Data not moved to production. ' + str(ex))
                return render_template('admin.html', title='Admin', form=form, staging=staging, production=production)
            else:
                db.session.add(ProductionData(data=staging))
                flash('Production updated')

        if form.copy_prod_to_new.data:
            flash('Copied production to new (no data changes)')
        db.session.commit()
        return redirect(url_for('admin'))

    return render_template('admin.html', title='Admin', form=form, staging=staging, production=production)


@app.route('/api/data.json')
@cache.cached(timeout=300, key_prefix="production_db")
def retrieve_production_data():
    try:
        query = db.session.query(ProductionData).order_by(text('-id')).first()
        if query is not None:
            result = query.data
    except Exception as exception:
        logging.error('Database error on PRODUCTION with exception: ' + str(exception))
        return Response(status=500)
    else:
        return result


@app.route('/staging/api/data.json')
@cache.cached(timeout=300, key_prefix="staging_db")
def retrieve_staging_data():
    try:
        query = db.session.query(StagingData).order_by(text('-id')).first()
        result = {}
        if query is not None:
            result = query.data
    except Exception as exception:
        logging.error('Database error on staging with exception: ' + str(exception))
        return Response(status=500)
    else:
        return result


def handle_ex(request, exception):
    print(exception)


def create_county_shipments(ppe_response):
    county_shipments = OrderedDict()
    ordered_counties = []
    errors = []
    try:
        total_shipments = ppe_response.json()['features']
        # Process total shipped to each county
        for raw_shipment in total_shipments:
            shipment = raw_shipment['attributes']
            county = shipment['jurisdiction']
            n95 = shipment['n95_masks']
            surgical_masks = shipment['surgical_masks']
            gowns = shipment['gowns']
            face_shields = shipment['face_shields']
            gloves = shipment['gloves']

            if county.lower() != "hood river":
                if county.lower() in county_shipments.keys():
                    current_county = county_shipments[county.lower()]
                    current_county['n95_masks'] += n95
                    current_county['surgical_masks'] += surgical_masks
                    current_county['gowns'] += gowns
                    current_county['face_shields'] += face_shields
                    current_county['gloves'] += gloves

                else:
                    ordered_counties.append(county.lower())
                    county_shipments[county.lower()] = {'n95_masks': n95, 'surgical_masks': surgical_masks,
                                                        'gowns': gowns, 'face_shields': face_shields, 'gloves': gloves}
    except Exception as exception:
        errors.append('Total county shipments: ' + str(exception))

    finally:
        return ordered_counties, county_shipments, errors


def retrieve_recent_shipments(shipments_response, count):
    # Process recent shipments
    errors = []
    recent_shipments = dict()
    try:
        all_shipments = shipments_response.json()['features']
        shipment_count = count

        for raw_shipment in reversed(all_shipments):
            if shipment_count <= 0:
                break

            shipment = raw_shipment['attributes']
            if shipment['jurisdiction'].lower() in COUNTIES and (shipment['surgical_masks'] > 0 or shipment['n95_masks'] > 0 or shipment['gowns'] > 0 or \
                    shipment['face_shields'] > 0 or shipment['gloves'] > 0):

                if shipment['jurisdiction'].lower() not in recent_shipments.keys():
                    shipment_count -= 1
                    recent_shipments[shipment['jurisdiction'].lower()] = {
                        'surgical_masks': shipment['surgical_masks'],
                        'n95_masks': shipment['n95_masks'],
                        'gowns': shipment['gowns'],
                        'face_shields': shipment['face_shields'],
                        'gloves': shipment['gloves'],
                        'date': shipment['_date']
                    }
    except Exception as exception:
        errors.append('Recent Shipments Error: ' + str(exception))
    finally:
        return recent_shipments, errors


@app.route('/api/all.json')
@cache.cached(timeout=600, key_prefix="all")
def retrieve_all_data():
    try:
        print("Getting cases data")
        urls = [
            # Cases API, ArcGIS
            'https://services.arcgis.com/uUvqNMGPm7axC2dD/arcgis/rest/services/'
            'COVID_Cases_Oregon_Public/FeatureServer/0/query?where=1%3D1&outFields=altName,'
            'Cases,Recovered,Deaths,GlobalID,NegativeTests,Population&returnGeometry=false&'
            'outSR=4326&f=json',
            # Shipments, ArcGIS
            'https://services.arcgis.com/uUvqNMGPm7axC2dD/arcgis/'
            'rest/services/PPE_Shipment_Tracking_for_Public_Display/'
            'FeatureServer/0/query?where=1%3D1&outFields=_date,jurisdiction,'
            'surgical_masks,n95_masks,gowns,face_shields,gloves&outSR=4326&f=json',
            # OHA
            'https://govstatus.egov.com/OR-OHA-COVID-19'
        ]
        rs = (grequests.get(u, timeout=5) for u in urls)
        async_reqs = grequests.map(rs, exception_handler=handle_ex)
        print(async_reqs)
        cases_response, ppe_response, capacity_response = tuple(async_reqs)

        ordered_counties, county_shipments, county_errors = create_county_shipments(ppe_response)
        recent_shipments, recent_shipment_errors = retrieve_recent_shipments(ppe_response, 4)
        capacity_data, capacity_errors = scraper.scrape_oha(capacity_response)

        # Process total cases (and append population to shipment table from above)
        county_array = cases_response.json()['features']

        total_cases = 0
        total_deaths = 0
        total_negative = 0
        cases_errors = []
        for county in county_array:
            attributes = county['attributes']
            county_name = attributes['altName'].lower().replace(' ', '_')
            total_cases += attributes['Cases']
            total_deaths += attributes['Deaths']
            total_negative += attributes['NegativeTests']

            county_shipments[county_name]['population'] = attributes['Population']
        cases_data = {'total': f'{total_cases:,}', 'deaths': f'{total_deaths:,}', 'negative': f'{total_negative:,}'}

    except Exception as exception:
        logging.error("Couldn't fetch case and shipment data: " + str(exception))
        return Response(status=500, response=str(exception))

    else:
        data = {'cases': cases_data,
                'capacity': capacity_data,
                'last_updated': time.time(),
                'errors': cases_errors + capacity_errors + recent_shipment_errors + county_errors,
                'shipments': {
                    'county_names': ordered_counties,
                    'total_by_county': county_shipments,
                    'recent_by_county': recent_shipments}
                }
        data.update(capacity_data)
        r = Response(status=200, response=json.dumps(data))
        r.headers['Content-Type'] = "application/json"
        return r


@app.route('/api/last-good.json')
@cache.cached(timeout=600, key_prefix="all-good")
def last_good_data():
    try:
        r = retrieve_all_data()
    except Exception as exception:
        logging.error(exception)
        return cache.get('last-good-data')
    if r.status_code != 200:
        logging.error('Problem getting data. Check logs.')
        return cache.get('last-good-data')
    cache.set('last-good-data', r, timeout=0)
    cache.set('last-good-time', datetime.now(), timeout=0)
    return r


@app.route('/healthcheckv2')
def health_check_v2():
    r = last_good_data()
    time_difference = datetime.now() - cache.get('last-good-time')
    difference_in_hours = time_difference.total_seconds() / 3600
    if difference_in_hours > 2:
        return Response(status=500, response="Data has been bad for 2 hours")

    all_errors = json.loads(r.data.decode("utf-8"))['errors']

    if len(all_errors) > 0:
        return Response(status=500, response="Errors: " + str(all_errors))
    return Response(status=200)


@app.route('/healthcheck')
def health_check():
    try:
        all_data = retrieve_all_data()
        if all_data.status_code != 200:
            return Response(status=500, response="Problem scraping data.")
        all_errors = json.loads(all_data.data.decode("utf-8"))['errors']
        if len(all_errors) > 0:
            return Response(status=500, response="Errors scraping data: " + str(all_errors))
        return Response(status=200)
    except Exception as exception:
        return Response(status=500, response=exception)


@app.route('/staging/logs')
@login_required
def logs():
    staging_ids = db.session.query(StagingData.id).order_by(text('-id'))
    production_ids = db.session.query(ProductionData.id).order_by(text('-id'))
    staging_ids_array = []
    production_ids_array = []
    for log_id, in staging_ids:
        staging_ids_array.append(log_id)

    for log_id, in production_ids:
        production_ids_array.append(log_id)
    return render_template('data_logs.html', title='Data Logs',
                           staging_ids=staging_ids_array, production_ids=production_ids_array)


@app.route('/staging/logs/<string:environment>/<int:log_id>')
@login_required
def log_by_environment_id(environment, log_id):
    if environment == "staging":
        log = db.session.query(StagingData).get(log_id)
    elif environment == "production":
        log = db.session.query(ProductionData).get(log_id)
    else:
        abort(404)
    return render_template('data_log_by_id.html', title='Staging Log: ' + str(log_id), log=log)



