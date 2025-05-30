.. BACmon documentation master file

Welcome to BACmon
=================

BACmon is a tool for monitoring BACnet/IP networks to be alerted to configuration
and performance problems. It passively receives messages that are broadcast on
the local network, decodes them, checks for certian 
kinds of traffic patterns and keeps counters for monitoring volume.

There are two pieces to BACmon.  The first is a daemon that gathers the packets,
does the decoding, and stores statistics in redis.  The second is a web presentation
tool developed using the bottle framework that can run standalone or as an 
Apache WSGI module (among others).

(more to come...)

Glossary
--------

.. toctree::
    :maxdepth: 2

    glossary.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

