# Chronology Statement

## Introduction

Dating events on the timeline is quite difficult in the humanities because it is often not possible to determine the
exact date. The OLDAP framework uses a point-in-time representation that allows for a great deal of flexibility. The
OLDAP implementation is based on the point-in-time representation of the
[_DaSCH Platform_](https://www.dasch.swiss/our-platform) and the [_NoatGoat_](https://nodegoat.net) product, but extends it.

Please note that this description does not imply the graphical user interface. A well-designed GUI will facilitate
the entry of chronology statements and offer for many options meaningfull default values.

The OLDAP implementation is based on the following
principles:

- The accuracy of a chronology statements is limited to *days*. It does not allow to record hours, minutes etc.
- The time specifications are linked to calendar specifications. The Gregorian, Julian, Jewish and Islamic calendars
  are supported.
- The data is stored internally in a calendar-agnostic and commensurable way, namely as a Julian Day Count (JDC).
- All time specifications are provided with an accuracy, i.e. they are stored as a time span. If the time specification
  is available exactly, the start and end of the time span will be equal.
- An accuracy can be specified for both the start and the end of the time period. The accuracy can be specified as
  YEAR, MONTH or DAY. If the precision is YEAR, January 1 is taken as the start of the time span and December 31 as the
  end (or the corresponding This makes it possible, for example, to specify a period, e.g. for the time of the
  composition of a work, “1820 - 3 March 1822”, which means that the composition was written between 1 January 1820 and
  3 March 1822 – the first performance was on 3 March, so the composition must have been finished by then at the latest.
- If the timing of events is not known or only vaguely known, but the sequence is clear, then an (imprecise) time span
  can also be defined relative to another point in time. With “before” and “after” the sequential order can be defined.
  Optionally, a delta can also be specified, which is stored in the form of days. For example, I can define that event
  B took place after event A, 30-40 days later.

### Sequences of chronology statements

If there are several chronology statements whose exact values are not known and therefore cover a time span, but the
sequence is known, the OLDAP ChronologyStatment allows to express the order of the statments.

### Adding comments

In order to add comments to a chronology statement, the standard RDFStar mechanisms can be used

## RDF Implementation

The basic resource class is `:OldapChronolgyStatement`, which is a RDF resource that is defined using SHACL and has an
OWL implementation to support reasoning. It has the following properties:

### :chronoStartJDC
Records the start of the time span as Julian Day count. The [_Julian Day Count_](https://en.wikipedia.org/wiki/Julian_day)
is a calendar independent way to designate a date. It's often used in Astronomy.

- *datatype*: `xsd:decimal`
- *required*: yes
- *multiple values*: no

### :chronoStartPrecision
Indicates to what precision the start of the time span is known. Accepted values are "YEAR", "MONTH", "DAY".

- *datatype*: `xsd:string` out of "YEAR"^^xsd:string, "MONTH"^^xsd:string, "DAY"^^xsd:string.
- *required*: yes
- *multiple values*: no

The following rules apply:

- "YEAR": the Julian Day count will be set to the January 1st of the given year.
- "MONTH": The Julian Day count will be set to the first day of the given month and year.
- "DAY": The Julian Day count will be set to the exact date as given.

### :chronoEndJDC
Records the end of the time span as Julian Day count. The [_Julian Day Count_](https://en.wikipedia.org/wiki/Julian_day)
is a calendar independent way to designate a date. It's often used in Astronomy.

- *datatype*: `xsd:decimal`
- *required*: yes
- *multiple values*: no

### :chronoEndPrecision
Indicates to what precision the end of the time span is known. Accepted values are "YEAR", "MONTH", "DAY".

- *datatype*: `xsd:string` out of `"YEAR"^^xsd:string`, `"MONTH"^^xsd:string`, `"DAY"^^xsd:string`.
- *required*: yes
- *multiple values*: no

The following rules apply:

- "YEAR": the Julian Day count will be set to the December 31st of the given year.
- "MONTH": The Julian Day count will be set to the last day of the given month and year.
- "DAY": The Julian Day counr will be set to the exact date as given.

### :chronoCalendar
Indicates which calendar the date has originally been given in. The following calendars will be supported:

- *datatype*: `xsd:string` out of `"GREGORIAN"^^xsd:string`, `"JULIAN"^^xsd:string`, `"HEBREW"^^xsd:string`, `"ISLAMIC"^^xsd:string`
- *required*: yes
- *multiple values*: no

This property gives a hint to the used in which calendar the chronology statement has been given. On retrieval,
conversions to other calendars are supported. 

*Note*: Both the start and end of the time span are assumed to be in the same calendar

### :chronoAfter
If there is a sequence of chronology statements, this property points to the previous statement.

- *datatype*: `:OldapChronolgyStatement` (URI)
- *required*: no
- *multiple values*: no

### :chronoMinDelta
An optional value to indicate how many days in *minimum* have passed since the previous chronology statement in the
sequence. The delta is given in days, where a year is considered to be 365 days and a month 30 days.

- *datatype*: xsd:decimal
- *required*: no
- *multiple values*: no

### :chronoMaxDelta
An optional value to indicate how many days *in maximum* have passed since the previous chronology statement in the
sequence. The delta is given in days, where a year is considered to be 365 days and a month 30 days.

- *datatype*: xsd:decimal
- *required*: no
- *multiple values*: no

## Examples

### Precise date

Let's assume that a given letter was written on the 23rd May of 1833. This woould be encoded as follows:

```trig
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

ex:Letter512 ex:writtenAtDate [
    a :OldapChronolgyStatement ;
    :chronoStartJDC "2390691.5"^^xsd:decimal ; # 1833-05-23
    :chronoStartPrecision "DAY"^^xsd:string ;
    :chronoEndJDC "2390691.5"^^xsd:decimal ; # 1833-05-23
    :chronoENDPrecision "DAY"^^xsd:string ;
    :chronoCalendar "GREGORIAN"^^xsd:string ;
] .
```

### Timespan

Let's assume that a given sculpture was made probably 1710 +/- 5 years (e.g. 1705-1715):

```trig
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

ex:Sculpture12 ex:created [
    a :OldapChronolgyStatement ;
    :chronoStartJDC "2343798,5"^^xsd:decimal ; # 1705-01-01
    :chronoStartPrecision "YEAR"^^xsd:string ;
    :chronoEndJDC "2347814,5"^^xsd:decimal ; # 1715-12-31
    :chronoENDPrecision "YEAR"^^xsd:string ;
    :chronoCalendar "GREGORIAN"^^xsd:string ;
] .
```


### Sequence of two events

Let's assume we have to events in a journey that took place at the same month, but we do not know the exact dates.
We even do not know how many days passed between the two events.

```trig
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/> .

ex:MeetingA ex:meetingAtDate [
    a :OldapChronolgyStatement ;
    :chronoStartJDC "2343798,5"^^xsd:decimal ; # 1705-01-01
    :chronoStartPrecision "YEAR"^^xsd:string ;
    :chronoEndJDC "2347814,5"^^xsd:decimal ; # 1715-12-31
    :chronoENDPrecision "YEAR"^^xsd:string ;
    :chronoCalendar "GREGORIAN"^^xsd:string ;
] .

ex:MeetingB ex:meetingAtDate [
    a :OldapChronolgyStatement ;
    :chronoStartJDC "2343798,5"^^xsd:decimal ; # 1705-01-01
    :chronoStartPrecision "YEAR"^^xsd:string ;
    :chronoEndJDC "2347814,5"^^xsd:decimal ; # 1715-12-31
    :chronoENDPrecision "YEAR"^^xsd:string ;
    :chronoCalendar "GREGORIAN"^^xsd:string ;
    :chronoAfter ex:MeetingA ;
] .
```

If we know that `ex:MeetingB` occured 5-7 days later, we could add
```trig
:chronoMinDelta "5.0"^^xsd:decimal ;
:chronoMaxDelta "7.0"^^xsd:decimal ;
```

### Adding a comment

The following sequence based on RDF*star would add a comment to the statement:

```trig
# Define the blank node and link it through an intermediate property
ex:Sculpture12 ex:creationDetails _:chronologyStatement .

_:chronologyStatement
    a :OldapChronologyStatement ;
    :chronoStartJDC "2343798.5"^^xsd:decimal ; # 1705-01-01
    :chronoStartPrecision "YEAR"^^xsd:string ;
    :chronoEndJDC "2347814.5"^^xsd:decimal ; # 1715-12-31
    :chronoEndPrecision "YEAR"^^xsd:string ;
    :chronoCalendar "GREGORIAN"^^xsd:string .

# Use the intermediate triple in RDF* for the comment
<< ex:Sculpture12 ex:creationDetails _:chronologyStatement >> rdfs:comment "According Sculpture Catalogue"^^xsd:string .
```


