# -*- coding: utf-8 -*-
#
# "TheVirtualBrain - Widgets" package
#
# (c) 2022-2023, TVB Widgets Team
#

class TVBExtUnicoreException(Exception):

    def __init__(self, message):
        super().__init__(message)
        self.message = str(message)

    def __str__(self):
        return self.message
