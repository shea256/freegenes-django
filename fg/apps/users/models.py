'''

Copyright (C) 2019 Vanessa Sochat.

This Source Code Form is subject to the terms of the
Mozilla Public License, v. 2.0. If a copy of the MPL was not distributed
with this file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''

from django.conf import settings
from django.contrib.auth.models import (
    AbstractUser, 
    BaseUserManager
)
from django.db.models.signals import post_save
from django.dispatch import receiver

from django.db import models

from rest_framework.authtoken.models import Token
from fg.apps.users.utils import get_usertoken
import os

################################################################################
# Supporting Functions
################################################################################


class CustomUserManager(BaseUserManager):
    '''Create and save a User with the given username, email and password.
    '''

    def _create_user(self, username, email, password,
                     is_staff, is_superuser, **extra_fields):
        if not username:
            raise ValueError('The given username must be set')

        email = self.normalize_email(email)
        user = self.model(username=username, email=email,
                          is_staff=is_staff, is_active=True, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email=None, password=None, **extra_fields):
        return self._create_user(username, email, password, False, False,
                                 **extra_fields)

    def create_superuser(self, username, email, password, **extra_fields):
        return self._create_user(username, email, password, True, True,
                                 **extra_fields)

    def add_superuser(self, user):
        ''' Intended for existing user'''
        user.is_superuser = True
        user.save(using=self._db)
        return user

    def add_staff(self, user):
        ''' Intended for existing user'''
        user.is_staff = True
        user.save(using=self._db)
        return user


class User(AbstractUser):
    active = models.BooleanField(default=True)

    # The user can choose to set his or her institution
    institution = models.ForeignKey('main.Institution', on_delete=models.PROTECT, default=None, null=True, blank=True)

    # has the user agreed to terms?
    agree_terms = models.BooleanField(default=False)
    agree_terms_date = models.DateTimeField(blank=True,
                                            default=None,
                                            null=True)

    def get_cart(self):
        '''Get a user's cart (an order that is not yet submit). A user
           is only allowed one order with this status and their association.
        '''
        for order in self.order_set.all():
            # if the order isn't ordered, it's the cart.
            if not order.ordered:
                return order

    def get_cart_items(self):
        '''get distribution items in a user's active cart. Useful for views
           to render a button as disabled or active depending on finding/not
           finding the distribution.
        '''
        distributions = []
        cart = self.get_cart()
        if cart:
            return cart.distributions.all()
        return distributions


    # Ensure that we can add staff / superuser and retain on logout
    objects = CustomUserManager()

    class Meta:
        app_label = 'users'

    def get_label(self):
        return "users"

    def token(self):
        return get_usertoken(self)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    ''' Create a token for the user when the user is created (with oAuth2)

        1. Assign user a token
        2. Assign user to default group

        Create a Profile instance for all newly created User instances. We only
        run on user creation to avoid having to check for existence on each call
        to User.save.

    '''
    if created:
        Token.objects.create(user=instance)
