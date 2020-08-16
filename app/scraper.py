import json

from bs4 import BeautifulSoup, Comment
import re
import time
import logging


def scrape_oha(response):
    errors = []
    all_content = BeautifulSoup(response.content, "html.parser", from_encoding="utf-8")
    comments = all_content.findAll(text=lambda text:isinstance(text, Comment))
    [comment.extract() for comment in comments]

    # # # Adult ICU Beds
    try:
        adult_icu_beds_row = all_content.find_all('td', string=re.compile("^Adult ICU"))

        adult_icu_available = adult_icu_beds_row[0].find_next_sibling().find_all(string=re.compile("\\d+"))[0]
        adult_icu_total = adult_icu_beds_row[0].find_next_sibling().find_next_sibling().find_all(string=re.compile("\\d+"))[0]
        if adult_icu_available is None or len(adult_icu_available) == 0:
            errors.append("Adult ICU Beds")
            adult_icu_available = "-"
        if adult_icu_total is None or len(adult_icu_total) == 0:
            errors.append("Adult ICU Beds")
            adult_icu_total = "-"
    except Exception as exception:
        logging.error(str(exception))
        adult_icu_available = "-"
        adult_icu_total = "-"
        errors.append("Adult ICU Beds")

    # Adult non ICU Beds
    try:
        adult_non_icu_beds_row = all_content.find_all('td', string=re.compile("^Adult non-ICU"))
        adult_non_icu_available = adult_non_icu_beds_row[0].find_next_sibling().find_all(string=re.compile("\\d+"))[0]
        adult_non_icu_total = adult_non_icu_beds_row[0].find_next_sibling().find_next_sibling().find_all(string=re.compile("\\d+"))[0]
        if adult_non_icu_available is None or len(adult_non_icu_available) == 0:
            errors.append("Adult non-ICU Beds")
        if adult_non_icu_total is None or len(adult_non_icu_total) == 0:
            errors.append("Adult non-ICU Beds")
    except Exception as exception:
        logging.error(str(exception))
        adult_non_icu_available = "-"
        adult_non_icu_total = "-"
        errors.append("Adult non-ICU Beds")

    # # Pediatric ICU Beds
    try:
        pediatric_nicu_beds_row = all_content.find_all('td', string=re.compile("^Pediatric NICU"))
        pediatric_nicu_available = pediatric_nicu_beds_row[0].find_next_sibling().find_all(string=re.compile("\\d+"))[0]
        pediatric_nicu_total = pediatric_nicu_beds_row[0].find_next_sibling().find_next_sibling().find_all(string=re.compile("\\d+"))[0]
        if pediatric_nicu_available is None or len(pediatric_nicu_available) == 0:
            errors.append("Pediatric ICU Beds")
        if pediatric_nicu_total is None or len(pediatric_nicu_total) == 0:
            errors.append("Pediatric ICU Beds")
    except Exception as exception:
        logging.error(str(exception))
        pediatric_nicu_available = "-"
        pediatric_nicu_total = "-"
        errors.append("Pediatric ICU Beds")

    # # Ventilators
    try:
        ventilators_row = all_content.find_all('td', string=re.compile("^Ventilators"))
        ventilators_available = ventilators_row[0].find_next_sibling().find_all(string=re.compile("\\d+"))[0]

        if ventilators_available is None or len(ventilators_available) == 0:
            errors.append('Ventilators')
            ventilators_available = "-"
    except Exception as exception:
        logging.error(str(exception))
        ventilators_available = "-"
        errors.append("Ventilators")

    # # Current and Suspected Hospitalized
    try:
        confirmed_suspected_hospitalized_row = all_content\
            .find_all('td', string=re.compile("(?im)Current hospitalized"))
        confirmed_suspected_hospitalized = confirmed_suspected_hospitalized_row[0].find_next_sibling()\
            .find_all(string=re.compile("\\d+"))[0]
        if confirmed_suspected_hospitalized is None or len(confirmed_suspected_hospitalized) == 0:
            errors.append('Hospitalized')
            confirmed_suspected_hospitalized = "-"
    except Exception as exception:
        logging.error(str(exception))
        confirmed_suspected_hospitalized = "-"
        errors.append("Hospitalized")

    # # Current and Suspected ICU
    try:
        confirmed_suspected_ICU_row = all_content\
            .find_all('td', string=re.compile("(?im)current patients in ICU"))
        confirmed_suspected_ICU = confirmed_suspected_ICU_row[0].find_next_sibling()\
            .find_all(string=re.compile("\\d+"))[0]
        if confirmed_suspected_ICU is None or len(confirmed_suspected_ICU) == 0:
            errors.append("In ICU")
            confirmed_suspected_ICU = "-"
    except Exception as exception:
        logging.error(str(exception))
        confirmed_suspected_ICU= "-"
        errors.append("In ICU")

    # # Current and Suspected Ventilators
    try:
        confirmed_suspected_ventilators_row = all_content\
            .find_all('td', string=re.compile("(?im)current patients on ventilators"))
        confirmed_suspected_ventilators = confirmed_suspected_ventilators_row[0].find_next_sibling()\
            .find_all(string=re.compile("\\d+"))[0]
        if confirmed_suspected_ventilators is None or len(confirmed_suspected_ventilators) == 0:
            errors.append('Used Ventilators')
            confirmed_suspected_ventilators = "-"
    except Exception as exception:
        logging.error(str(exception))
        confirmed_suspected_ventilators = "-"
        errors.append("Used Ventilators")

    return {
        # "cases": {
        #     "total": positive_cases,
        #     "deaths": total_deaths,
        #     "tested": total_tested
        # },
        "capacity": {
            "adult_icu_available": adult_icu_available,
            "adult_icu_total": adult_icu_total,
            "adult_non_icu_available": adult_non_icu_available,
            "adult_non_icu_total": adult_non_icu_total,
            "pediatric_icu_available": pediatric_nicu_available,
            "pediatric_icu_total": pediatric_nicu_total
        },
        "hospitalized": {
            "total": confirmed_suspected_hospitalized,
            "icu": confirmed_suspected_ICU
        },
        "ventilators": {
            "available": ventilators_available,
            "in_use": confirmed_suspected_ventilators
        },
        "operation_status": {
            "ecc": "Standby",
            "esf8": "Activated"
        },
        "esf": {
            "mass_care_6": "Status Unavailable",
            "health_medical_8": "Status Unavailable",
            "patient_movement": "Status Unavailable",
            "public_health": "Status Unavailable"
        }
    }, errors



