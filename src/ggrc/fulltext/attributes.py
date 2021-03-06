# Copyright (C) 2017 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

""" This module collect all custom full text attributes classes"""

from collections import defaultdict

import datetime

from flask import g

from ggrc.utils import date_parsers
from ggrc.fulltext.mixin import Indexed

EMPTY_SUBPROPERTY_KEY = ''


class FullTextAttr(object):
  """Custom full text index attribute class

  Allowed to add full text search rule for model with custom alias,
  getting value rule and subproperties.
  Alias should be a string that will be used as search field.
  Value can be string or callable.
  If value is string, then the stored value will be the current instance
  attribute value.
  If value is callable, then the stored value will be the result of
  called value with current instance as attribute.
  Subproperties may be empty or a list of strings. Each element of the list
  should be an attribute of the stored value.
  The first subproperty in the list - the one used for sorting.
  """

  SUB_KEY_TMPL = "{id_val}-{sub}"

  def __init__(self, alias, value, subproperties=None, with_template=True):
    self.alias = alias
    self.value = value
    self.subproperties = subproperties or [EMPTY_SUBPROPERTY_KEY]
    self.with_template = with_template
    self.is_sortable = EMPTY_SUBPROPERTY_KEY not in self.subproperties

  def get_attribute_name(self, instance):
    """Get attribute's name from it's alias

    If template exists for the property, it's being applied
    """
    if isinstance(instance, Indexed):
      property_tmpl = instance.PROPERTY_TEMPLATE
    else:
      property_tmpl = u"{}"

    if self.with_template:
      return property_tmpl.format(self.alias)
    return self.alias

  def get_value_for(self, instance):
    """Get value from sended instance using 'value' rule"""
    if callable(self.value):
      return self.value(instance)
    return getattr(instance, self.value)

  def get_property_for(self, instance):
    """Collect property dict for sended instance"""
    value = self.get_value_for(instance)
    results = {}
    sorted_dict = {}
    sorting_subprop = self.subproperties[0]
    for subprop in self.subproperties:
      if value is not None and subprop != EMPTY_SUBPROPERTY_KEY:
        subprop_key = self.SUB_KEY_TMPL.format(id_val=value.id, sub=subprop)
        result = getattr(value, subprop)
        results[subprop_key] = result
        if result and subprop == sorting_subprop:
          sorted_dict[value.id] = unicode(result)
      else:
        results[subprop] = value
    if self.is_sortable:
      results['__sort__'] = u':'.join(sorted(sorted_dict.values()))
    return {self.get_attribute_name(instance): results}

  # pylint: disable=unused-argument
  @staticmethod
  def get_filter_value(value, operation):
    return value


class CustomRoleAttr(FullTextAttr):
  """Custom index attribute class for custom roles"""
  # pylint: disable=too-few-public-methods
  def __init__(self, alias):
    super(CustomRoleAttr, self).__init__(alias, alias)
    self.with_template = False

  def get_property_for(self, instance):
    """Returns index properties of all custom roles for a given instance"""
    results = {}
    sorted_roles = defaultdict(list)
    for acl in getattr(instance, self.alias, []):
      ac_role = acl.ac_role.name
      person_id = acl.person.id
      if not results.get(acl.ac_role.name, None):
        results[acl.ac_role.name] = {}
      sorted_roles[ac_role].append(acl.person.user_name)
      results[ac_role]["{}-email".format(person_id)] = acl.person.email
      results[ac_role]["{}-name".format(person_id)] = acl.person.name
      results[ac_role]["{}-user_name".format(person_id)] = acl.person.user_name
    for role in sorted_roles:
      results[role]["__sort__"] = u':'.join(sorted(sorted_roles[role]))
    return results


class MultipleSubpropertyFullTextAttr(FullTextAttr):
  """Custom full text index attribute class for multiple return values

  subproperties required for this class
  this class required for store in full text search more than 1 returned value
  this values should be instances with `id` attribute or None values
  In the case if values is None id in subquery template will be set up as
  `EMPTY` value
  """

  def __init__(self, *args, **kwargs):
    super(MultipleSubpropertyFullTextAttr, self).__init__(*args, **kwargs)
    assert EMPTY_SUBPROPERTY_KEY not in self.subproperties
    assert self.is_sortable

  def get_property_for(self, instance):
    """Collect property for sended instance"""
    values = self.get_value_for(instance)
    results = {}
    sorted_dict = {}
    sorting_subprop = self.subproperties[0]
    for sub in self.subproperties:
      for value in values:
        if value is not None:
          sub_key = self.SUB_KEY_TMPL.format(id_val=value.id, sub=sub)
          result = getattr(value, sub)
          results[sub_key] = result
          if result and sub == sorting_subprop:
            sorted_dict[value.id] = unicode(result)
        else:
          sub_key = self.SUB_KEY_TMPL.format(id_val='EMPTY', sub=sub)
          results[sub_key] = None
    if self.is_sortable:
      results['__sort__'] = u':'.join(sorted(sorted_dict.values()))
    return {self.get_attribute_name(instance): results}


# pylint: disable=too-few-public-methods
class DatetimeValue(object):
  """Mixin setup if expected filter value is datetime.

  This mixin should be used for filtering datetime fields values only.
  """

  @staticmethod
  def get_filter_value(value, operation):
    """returns parsed datetime pairs for selected operation"""
    converted_pairs = date_parsers.parse_date(unicode(value))
    if not converted_pairs:
      return
    date_dict = {
        "=": converted_pairs,
        "~": converted_pairs,
        "!~": (converted_pairs[1], converted_pairs[0]),
        "!=": (converted_pairs[1], converted_pairs[0]),
        ">": (converted_pairs[1], None),
        "<": (None, converted_pairs[0]),
        ">=": (converted_pairs[0], None),
        "<=": (None, converted_pairs[1]),
    }
    return date_dict.get(operation)


class DateValue(DatetimeValue):
  """Mixin setup if expected filter value is date

  This mixin should be used for filtering date fields values only.
  """

  def get_filter_value(self, value, operation):
    results = super(DateValue, self).get_filter_value(value, operation)
    if not results:
      return
    return [i.date() if i else i for i in results]


class TimezonedDatetimeValue(DatetimeValue):
  """Mixin setup if expected filter value is datetime depended from timezone.

  This mixin should be used for filtering datetime fields values only.
  """

  def get_filter_value(self, value, operation):
    """returns parsed datetime pairs for selected operation"""
    if getattr(g, "user_timezone_offset", None):
      minutes_offset = int(g.user_timezone_offset)
    else:
      minutes_offset = 0
    offset = datetime.timedelta(minutes=minutes_offset)
    converted_pairs = super(TimezonedDatetimeValue, self).get_filter_value(
        value, operation
    )
    if not converted_pairs:
      return converted_pairs
    return [(p - offset) if p else p for p in converted_pairs]


DatetimeFullTextAttr = type(
    "DatetimeFullTextAttr", (TimezonedDatetimeValue, FullTextAttr), {})


DateFullTextAttr = type("DateFullTextAttr", (DateValue, FullTextAttr), {})


DatetimeMultipleSubpropertyFullTextAttr = type(
    "DatetimeMultipleSubpropertyFullTextAttr",
    (TimezonedDatetimeValue, MultipleSubpropertyFullTextAttr),
    {},
)


DateMultipleSubpropertyFullTextAttr = type(
    "DateMultipleSubpropertyFullTextAttr",
    (DateValue, MultipleSubpropertyFullTextAttr),
    {},
)
