Miscellaneous
=============

``CharBasedParser``'s design of match locations behavior of ``\n``
------------------------------------------------------------------
A non-``\n`` character advances the :ref:`location<location_format>` by ``colno += 1``, and a ``\n`` character advances the location by ``lineno += 1; colno = 0``.

Notably, a string ending with a ``\n``

::

    @base CharBasedParser
    @location_format "(start, end)"
    start: "a\n" { LOCATIONS }

is considered to have its end location at the start of a new line: ``((0, 0), (1, 0))``. The behavior could arguably be to set the end location on the same line, e.g. ``((0, 0), (0, 2))``, which gives the advantage that when indenting all lines and computing the changed locations, all that is needed is to add a fixed amount to the colno. However, that means given a location span it requires looking back at the original text to determine how many "lines" were spanned, if having a trailing newline counts as adding a line (e.g. in many text editors). The current default also has the advantage that that ``"\na"`` spans 1 line is consistent with ``"a\n"`` spanning 1 line (if in the sense that they both conveniently have ``end_lineno - start_lineno == 1``).

I have personally not hit a use case where a different ``\n`` location behavior is substantially more convenient, but feel free to let me know!

``\r`` and ``\r\n`` support?
----------------------------
Not yet. Don't expect. Might not have energy to implement. :()