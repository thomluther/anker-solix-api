# -*- mode: python: coding: utf-8 -*-
"""
a collection of helper functions for pyscripts
"""
import getpass
import logging
import os

CONSOLE: logging.Logger = logging.getLogger("console")

# Optional default Anker Account credentials to be used
_CREDENTIALS = {
    "USER": os.getenv("USER"),
    "PASSWORD": os.getenv("PASSWORD"),
    "COUNTRY": os.getenv("COUNTRY"),
}


def user():
    """
    Get anker account user
    """
    if _CREDENTIALS.get("USER"):
        return _CREDENTIALS["USER"]
    CONSOLE.info("\nEnter Anker Account credentials:")
    username = input("Username (email): ")
    while not username:
        username = input("Username (email): ")
    return username


def password():
    """
    Get anker account password
    """
    if _CREDENTIALS.get("PASSWORD"):
        return _CREDENTIALS["PASSWORD"]
    pwd = getpass.getpass("Password: ")
    while not pwd:
        pwd = getpass.getpass("Password: ")
    return pwd


def country():
    """
    Get anker account country
    """
    if _CREDENTIALS.get("COUNTRY"):
        return _CREDENTIALS["COUNTRY"]
    countrycode = input("Country ID (e.g. DE): ")
    while not countrycode:
        countrycode = input("Country ID (e.g. DE): ")
    return countrycode
