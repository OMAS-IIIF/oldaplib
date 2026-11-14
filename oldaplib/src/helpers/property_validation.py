"""Shared OLDAP scalar constraints for instance and annotation properties."""
import re
from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.observable_set import ObservableSet
from oldaplib.src.xsd.xsd_string import Xsd_string
from oldaplib.src.helpers.oldaperror import OldapErrorInconsistency, OldapErrorValue


def validate_value(values, property, other_values=None, *, annotation=False):
    """Validate typed values using a PropertyClass and optional sibling values.

    Coercion, cardinality, link visibility and ownership belong to the caller.
    No resource instance or Thing audit metadata is needed for field validation.
    """
    other_values = other_values or {}
    if property.get(PropClassAttr.LANGUAGE_IN) is not None:  # testing for LANGUAGE_IN conformance
        if not isinstance(values, LangString):
            raise OldapErrorInconsistency(f'Property {property.property_class_iri} with LANGUAGE_IN requires datatype rdf:langstring, got {type(values).__name__}.')
        for lang, dummy in values.items():
            if not lang in property[PropClassAttr.LANGUAGE_IN]:
                raise OldapErrorValue(f'Property {property.property_class_iri} with LANGUAGE_IN={property[PropClassAttr.LANGUAGE_IN]} has invalid language "{lang.value}"')
    if property.get(PropClassAttr.UNIQUE_LANG) and not annotation:
        # Preserve the established resource validation path. Annotation fields
        # additionally validate their scalar content after language constraints.
        return
    if annotation and isinstance(values, LangString):
        values = [Xsd_string(str(text)) for _, text in values.items()]
    if property.get(PropClassAttr.IN) is not None:
        if property.datatype is None:  # no defined datatype, e.h.sh:IRI
            tmpinset = {str(x) for x in property[PropClassAttr.IN]}
            if isinstance(values, (list, tuple, set, ObservableSet)):
                for val in values:
                    if not str(val) in tmpinset:
                        raise OldapErrorValue(
                            f'Property {property} with IN={property[PropClassAttr.IN]} has invalid value "{val}"')
            else:
                if not str(values) in tmpinset:
                    raise OldapErrorValue(f'Property {property.property_class_iri} with IN={property[PropClassAttr.IN]} has invalid value "{values}"')
        else:
            if isinstance(values, (list, tuple, set, ObservableSet)):
                for val in values:
                    if not val in property[PropClassAttr.IN]:
                        raise OldapErrorValue(
                            f'Property {property} with IN={property[PropClassAttr.IN]} has invalid value "{val}"')
            else:
                if not values in property[PropClassAttr.IN]:
                    raise OldapErrorValue(f'Property {property.property_class_iri} with IN={property[PropClassAttr.IN]} has invalid value "{values}"')
    if property.get(PropClassAttr.MIN_LENGTH) is not None:
        if isinstance(values, (list, tuple, set, ObservableSet)):
            for val in values:
                l = 0
                try:
                    l = len(val)
                except TypeError:
                    raise OldapErrorInconsistency(f'Property {property} with MIN_LENGTH={property[PropClassAttr.MIN_LENGTH]} has no length.')
                if l < property[PropClassAttr.MIN_LENGTH]:
                    raise OldapErrorInconsistency(f'Property {property} with MIN_LENGTH={property[PropClassAttr.MIN_LENGTH]} has length "{len(val)}".')
        else:
            l = 0
            try:
                l = len(values)
            except TypeError:
                raise OldapErrorInconsistency(f'Property {property} with MIN_LENGTH={property[PropClassAttr.MIN_LENGTH]} has no length.')
            if l < property[PropClassAttr.MIN_LENGTH]:
                raise OldapErrorInconsistency(f'Property {property} with MIN_LENGTH={property[PropClassAttr.MIN_LENGTH]} has length "{len(values)}".')
    if property.get(PropClassAttr.MAX_LENGTH) is not None:
        if isinstance(values, (list, tuple, set, ObservableSet)):
            for val in values:
                l = 0
                try:
                    l = len(val)
                except TypeError:
                    raise OldapErrorInconsistency(f'Property {property} with MAX_LENGTH={property[PropClassAttr.MAX_LENGTH]} has no length.')
                if l > property[PropClassAttr.MAX_LENGTH]:
                    raise OldapErrorInconsistency(f'Property {property} with MIN_LENGTH={property[PropClassAttr.MAX_LENGTH]} has length "{len(val)}".')
        else:
            l = 0
            try:
                l = len(values)
            except TypeError:
                raise OldapErrorInconsistency(
                    f'Property {property} with MAX_LENGTH={property[PropClassAttr.MAX_LENGTH]} has no length.')
            if l > property[PropClassAttr.MAX_LENGTH]:
                raise OldapErrorInconsistency(f'Property {property} with MIN_LENGTH={property[PropClassAttr.MAX_LENGTH]} has length "{len(values)}".')

    if property.get(PropClassAttr.PATTERN) is not None:
        if isinstance(values, (list, tuple, set, ObservableSet)):
            for val in values:
                if not re.fullmatch(str(property[PropClassAttr.PATTERN]), str(val)):
                    raise OldapErrorInconsistency(f'Property {property} with PATTERN={property[PropClassAttr.PATTERN]} does not conform ({val}).')
        else:
            if not re.fullmatch(str(property[PropClassAttr.PATTERN]), str(values)):
                raise OldapErrorInconsistency(f'Property {property} with PATTERN={property[PropClassAttr.PATTERN]} does not conform ({values}).')

    if property.get(PropClassAttr.MIN_EXCLUSIVE) is not None:
        if isinstance(values, (list, tuple, set, ObservableSet)):
            for val in values:
                v: bool | None = None
                try:
                    v = val > property[PropClassAttr.MIN_EXCLUSIVE]
                except TypeError:
                    raise OldapErrorInconsistency(f'Property {property} with MIN_EXCLUSIVE={property[PropClassAttr.MIN_EXCLUSIVE]} cannot be compared to "{val}".')
                if not v:
                    raise OldapErrorInconsistency(f'Property {property} with MIN_EXCLUSIVE={property[PropClassAttr.MIN_EXCLUSIVE]} has invalid "{val}".')
        else:
            v: bool | None = None
            try:
                v = values > property[PropClassAttr.MIN_EXCLUSIVE]
            except TypeError:
                raise OldapErrorInconsistency(f'Property {property} with MIN_EXCLUSIVE={property[PropClassAttr.MIN_EXCLUSIVE]} cannot be compared to "{values}".')
            if not v:
                raise OldapErrorInconsistency(f'Property {property} with MIN_EXCLUSIVE={property[PropClassAttr.MIN_EXCLUSIVE]} has invalid "{values}".')

    if property.get(PropClassAttr.MIN_INCLUSIVE) is not None:
        if isinstance(values, (list, tuple, set, ObservableSet)):
            for val in values:
                v: bool | None = None
                try:
                    v = val >= property[PropClassAttr.MIN_INCLUSIVE]
                except TypeError:
                    raise OldapErrorInconsistency(f'Property {property} with MIN_EXCLUSIVE={property[PropClassAttr.MIN_INCLUSIVE]} cannot be compared to "{val}".')
                if not v:
                    raise OldapErrorInconsistency(f'Property {property} with MIN_EXCLUSIVE={property[PropClassAttr.MIN_INCLUSIVE]} has invalid "{val}".')
        else:
            v: bool | None = None
            try:
                v = values >= property[PropClassAttr.MIN_INCLUSIVE]
            except TypeError:
                raise OldapErrorInconsistency(f'Property {property} with MIN_EXCLUSIVE={property[PropClassAttr.MIN_INCLUSIVE]} cannot be compared to "{values}".')
            if not v:
                raise OldapErrorInconsistency(f'Property {property} with MIN_EXCLUSIVE={property[PropClassAttr.MIN_INCLUSIVE]} has invalid "{values}".')

    if property.get(PropClassAttr.MAX_EXCLUSIVE) is not None:
        if isinstance(values, (list, tuple, set, ObservableSet)):
            for val in values:
                v: bool | None = None
                try:
                    v = val < property[PropClassAttr.MAX_EXCLUSIVE]
                except TypeError:
                    raise OldapErrorInconsistency(f'Property {property} with MAX_EXCLUSIVE={property[PropClassAttr.MAX_EXCLUSIVE]} cannot be compared to "{val}".')
                if not v:
                    raise OldapErrorInconsistency(f'Property {property} with MAX_EXCLUSIVE={property[PropClassAttr.MAX_EXCLUSIVE]} has invalid "{val}".')
        else:
            v: bool | None = None
            try:
                v = values < property[PropClassAttr.MAX_EXCLUSIVE]
            except TypeError:
                raise OldapErrorInconsistency(f'Property {property} with MAX_EXCLUSIVE={property[PropClassAttr.MAX_EXCLUSIVE]} cannot be compared to "{values}".')
            if not v:
                raise OldapErrorInconsistency(f'Property {property} with MAX_EXCLUSIVE={property[PropClassAttr.MAX_EXCLUSIVE]} has invalid "{values}".')


    if property.get(PropClassAttr.MAX_INCLUSIVE) is not None:
        if isinstance(values, (list, tuple, set, ObservableSet)):
            for val in values:
                v: bool | None = None
                try:
                    v = val <= property[PropClassAttr.MAX_INCLUSIVE]
                except TypeError:
                    raise OldapErrorInconsistency(f'Property {property} with MAX_INCLUSIVE={property[PropClassAttr.MAX_INCLUSIVE]} cannot be compared to "{val}".')
                if not v:
                    raise OldapErrorInconsistency(f'Property {property} with MAX_INCLUSIVE={property[PropClassAttr.MAX_INCLUSIVE]} has invalid "{val}".')
        else:
            v: bool | None = None
            try:
                v = values <= property[PropClassAttr.MAX_INCLUSIVE]
            except TypeError:
                raise OldapErrorInconsistency(
                    f'Property {property} with MAX_INCLUSIVE={property[PropClassAttr.MAX_INCLUSIVE]} cannot be compared to "{values}".')
            if not v:
                raise OldapErrorInconsistency(
                    f'Property {property} with MAX_INCLUSIVE={property[PropClassAttr.MAX_INCLUSIVE]} has invalid "{values}".')

    if property.get(PropClassAttr.LESS_THAN) is not None:
        target = property[PropClassAttr.LESS_THAN]
        key = target.as_qname if getattr(target, "is_qname", False) else (Context(name=property._con.context_name).iri2qname(str(target)) or target)
        comparison_values = other_values.get(key)
        if comparison_values is not None and not isinstance(comparison_values, (list, tuple, set, ObservableSet)):
            comparison_values = [comparison_values]
        if comparison_values:
            b: bool | None = None
            try:
                min_other_value = min(comparison_values)
                if not isinstance(values, (list, tuple, set, ObservableSet)):
                    _values = [values]
                else:
                    _values = values
                max_value = max(_values)
                b = max_value < min_other_value
            except TypeError:
                raise OldapErrorInconsistency(
                    f'Property {property} with LESS_THAN={property[PropClassAttr.LESS_THAN]} cannot be compared to "{values}".')
            if not b:
                raise OldapErrorInconsistency(
                    f'Property {property} with LESS_THAN={property[PropClassAttr.LESS_THAN]} has invalid value: "{max_value}" NOT LESS_THAN "{min_other_value}".')
    if property.get(PropClassAttr.LESS_THAN_OR_EQUALS) is not None:
        target = property[PropClassAttr.LESS_THAN_OR_EQUALS]
        key = target.as_qname if getattr(target, "is_qname", False) else (Context(name=property._con.context_name).iri2qname(str(target)) or target)
        comparison_values = other_values.get(key)
        if comparison_values is not None and not isinstance(comparison_values, (list, tuple, set, ObservableSet)):
            comparison_values = [comparison_values]
        if comparison_values:
            b: bool | None = None
            try:
                min_other_value = min(comparison_values)
                if not isinstance(values, (list, tuple, set, ObservableSet)):
                    _values = [values]
                else:
                    _values = values
                max_value = max(_values)
                b = max_value <= min_other_value
            except TypeError:
                raise OldapErrorInconsistency(
                    f'Property {property} with LESS_THAN={property[PropClassAttr.LESS_THAN_OR_EQUALS]} cannot be compared "{values}".')
            if not b:
                raise OldapErrorInconsistency(
                    f'Property {property} with LESS_THAN={property[PropClassAttr.LESS_THAN_OR_EQUALS]} has invalid value: "{max_value}" NOT LESS_THAN "{min_other_value}".')

