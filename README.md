Tool to automatically replace `import *` imports with explicit imports

Requires pyflakes. Somewhat inspired by autoflake.

Limitations:

- Only works with relative imports at the moment
- Does not work correctly with recursive star imports
- Assumes only names in the current file are used by star imports
