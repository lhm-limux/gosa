# -*- coding: utf-8 -*-
import re
from gosa.common.env import Environment


class PhoneNumberResolver(object):
    priority = 10
    replace = []

    def __init__(self):
        self.env = env = Environment.getInstance()

        # read replacement configuration
        if not PhoneNumberResolver.replace:
            for opt in env.config.getOptions("resolver-replace"):
                itm = env.config.getOption(opt, "resolver-replace")
                res = re.search("^\"(.*)\",\"(.*)\"$", itm)
                res = re.search("^\"(.*)\"[\s]*,[\s]*\"(.*)\"$", itm)

                if res:
                    PhoneNumberResolver.replace.append([res.group(1), res.group(2)])

    def replaceNumber(self, number):
        # Apply configured substitutions on number
        for rep in PhoneNumberResolver.replace:
            number = re.sub(rep[0], rep[1], number)

        return number

    def resolve(self):
        raise NotImplementedError("resolve is not implemented")
