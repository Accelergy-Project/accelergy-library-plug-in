# Library Accelergy Plug-in
This Accelergy plug-in provides a library of components from published works.
It is intended to be used to rapidly model prior works and to provide a common
set of components for comparison.

## Installing
The Library plug-in requires Accelergy v0.4.0 or later. It can be installed
with pip:
```
git clone git@github.com:Accelergy-Project/accelergy-library-plug-in.git
cd accelergy-library-plug-in
pip3 install .
```

## Creating Library Entries
Each Library entry is a CSV file that records the name and relevant attributes
of a component and provides energy/area estimates for the component. The name
of the CSV file is the name of the component. 

If you choose to add new entries, you may either update the library and
reinstall, or you may edit the installed files directly in
`share/accelergy/estimation_plug_ins/accelergy-library-plugin`.

### Entry Format
Entries are stored in subdirectories of the "library" directory. An entry CSV
is named the same name as the component. It is organized as follows:
```
attr1, attr2, ..., attrN, energy, area, action
val1,  val2,  ..., valN,  energy, area, action_name_1|action_name_2|...
val1,  val2,  ..., valN,  energy, area, action_name_3|action_name_4|...
...
```
Each row can contain a different parameterization of the component, a different
action, or both.

The energy for an action is given in pJ and the area is given in um^2. If an
attribute is the technology node, the attribute name should be "technology" and
the value should be given in nm.

Special characters:
- `#` is a comment character. Any text after a `#` is ignored.
- `,` is the delimiter character.
- `|` is the OR delimiter character. Multiple actions can be specified in a
  single row by separating them with `|`. Multiple attributes (e.g.
  "width|datawidth") can also be OR'ed. If multiple OR'ed attributes match,
  then at most one of the matching attributes will be scaled.
- `*` is the wildcard character. It can be used to specify that a parameter is
  not relevant to the action. For example, if a component has a parameter that
  is only relevant to the `read` action, then the corresponding cell for the
  `write` action can be filled with `*`. Wildcards can also be expressed by
  leaving a cell blank.

All entries are case-insensitive.

### Required Actions
Components are required to have a read, write, update, and leak action. Other
actions are optional. This allows Library components to be realized directly in
Timeloop architectures.

Often, some of these required actions may not make sense for a component. For
exmaple, a digital multiplier may only have "multiply" and "leak" actions. We
follow the following convention for these cases:
- If the "read" action does not make sense for a component, then it is set to
the typical action for the component. For example, a multiplier's "read" action
is set to "multiply".
- If "write"/"update" actions do not make sense for a component, then they are
set to "leak".

In our multiplier example, we would create an entry multiplier.csv that looks
like:
```
width_a|datawidth_a, width_b|datawidth_b, technology, global_cycle_seconds, energy, area, action
32,                  32,                  65,         1e-9                  5,      300,  multiply|read
32,                  32,                  65,         1e-9,                 0.01,   300,  leak
32,                  32,                  65,         1e-9                  0,      300,  write|update
```

### Pointers To Other Entries 
If a work uses components from another work, it may be easier to create a
pointer to the other work's entry rather than re-creating the component. This
can be done by creating a _pointers.txt file in a subdirectory of the library
directory. A _pointers.txt file can contain any number of lines. Each line is a
pointer, formatted "new_name: pointed_to_name" without the quotes. 

## How Energy/Area Is Estimated
The Library plug-in will attempt to match components given a query from
Accelergy. Given a request, the Library plug-in will find its best-matching
entry using the following algorithm:
- To provide area, the entry name must equal the query name. To provide energy,
  the entry name and action must match the query name and action, respectively.
- If multiple entries meet these criteria, the number of identical attributes
  is counted. An attribute is identical if it has the same value in the entry
  and the query, or if the entry value is a wildcard or unspecified. An
  entry attribute is ignored if it is unspecified in the query.
- For the chosen entry, there may be attributes that are not equal. The 
  Library plug-in will attempt to scale the entry attributes to match the
  query attributes. If any attributes cannot be scaled, then the entry is not
  chosen.
- If multiple entries match the query and they have the same number of matching
  attributes, then the first entry is chosen.

## Scaling Parameters
The Library plug-in will attempt to scale the entry attributes to match the
query attributes. The following parameters can be scaled. When not otherwise
specified, leakage scales linearly with energy:
- `technology` scales energy/area based on Aaron Stillmaker, Bevan Baas, Scaling
  equations for the accurate prediction of CMOS device performance from 180nm
  to 7nm, Integration, Volume 58, 2017, Pages 74-81, ISSN 0167-9260,
  https://doi.org/10.1016/j.vlsi.2017.02.002.
- `resolution` scales energy/area exponentially with a factor of 2
- `voltage` scales energy quadratically, and leakage linearly.
- `global_cycle_seconds` scales leakage linearly
- `width`, `datawidth`, `width_a`, `width_b`, `datawidth_a`,
  and `datawidth_b`, scale energy/area linearly
- `resolution` scales energy/area exponentially with a factor of 2
- `depth` scales area linearly, energy with a power of 1.56 / 2 to match the
  buffer energy scaling of CACTI. S. J. E. Wilton and N. P. Jouppi, "CACTI: an
  enhanced cache access and cycle time model," in IEEE Journal of Solid-State
  Circuits, vol. 31, no. 5, pp. 677-688, May 1996, doi: 10.1109/4.509850.
- 
- `no_scale_area` disables scaling area for any other parameters.
- `no_scale_energy` disables scaling energy for any other parameters.


## Contributing: Adding or Updating Numbers from Your Work 
We would be happy to update these models given a pull request. Please see
"Creating Library Entries" and format your entries to match the existing
entries. If you have any questions, we would be happy to help.

Note that we will only accept entries that are published or backed by public
data. Citations are required for all entries.
