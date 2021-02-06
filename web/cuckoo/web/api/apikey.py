# Copyright (C) 2020 - 2021 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import secrets
import string
import django
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from tabulate import tabulate

from .startup import set_path_settings

class APIKeyError(Exception):
    pass

def print_api_keys():
    rows = [
        (token.user.id, token.user.username, token.user.is_staff,
        token.created.strftime("%Y-%m-%d %H:%M"), token.key)
        for token in Token.objects.all()
    ]
    if not rows:
        return

    print(tabulate(
        rows, ("Key ID", "Owner", "Is admin", "Created on", "API Key"),
        tablefmt="github"
    ))

def create_key(owner, admin=False):
    from django.db.utils import IntegrityError

    passw = "".join(
        secrets.choice(string.ascii_letters + string.digits) for i in range(32)
    )
    try:
        user = User.objects.create_user(
            username=owner, password=passw, is_staff=admin
        )
    except IntegrityError as e:
        raise APIKeyError(f"Owner {owner} already exists.")

    token = Token.objects.create(user=user)
    return token.key, user.id

def delete_key(identifier):
    return User.objects.filter(id=identifier).delete()[0]

def delete_all():
    return User.objects.all().delete()[0]

def count_key():
    return Token.objects.count()
