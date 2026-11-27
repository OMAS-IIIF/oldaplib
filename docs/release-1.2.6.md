# oldaplib 1.2.6

Staging folder inventory can be read while an archive writer holds the gate.
The inventory checks folder access, the visible page and the folder revision
before returning results.

The Jena service reports actor-bound transaction status. After an ambiguous
commit or abort response, the Python client checks that status once. A confirmed
end closes the writer's journal entry. An unresolved outcome retains the gate
for operator recovery.

Deploy the matching Jena service before updating the API and other Python
workers. The PyPI distributions contain the Python library. Build the Jena
service separately from the same release tag.
