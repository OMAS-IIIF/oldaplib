# Explicit user decision, 2026-11-02: retain DATA_PERMISSIONS when the same
# asserted WriterRecoveryOperator membership has both defaults in this snapshot.
# Run only on the isolated home.org Jena target after inventory/backup.
# Orphan memberships remain untouched and inactive. No membership is added.
PREFIX oldap: <http://oldap.org/base#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
WITH oldap:admin
DELETE { ?grant oldap:hasDefaultDataPermission oldap:DATA_VIEW }
WHERE {
  ?user oldap:hasRole oldap:WriterRecoveryOperator .
  ?grant rdf:reifies <<( ?user oldap:hasRole oldap:WriterRecoveryOperator )>> ;
         oldap:hasDefaultDataPermission oldap:DATA_VIEW .
  ?other rdf:reifies <<( ?user oldap:hasRole oldap:WriterRecoveryOperator )>> ;
         oldap:hasDefaultDataPermission oldap:DATA_PERMISSIONS .
}
