"""pytest config for project-init's own tests.

tests/fixtures/ holds repo trees that the tests copy into temp dirs. Their test files are
data here, so pytest must not collect them from this folder.
"""

collect_ignore = ["fixtures"]
