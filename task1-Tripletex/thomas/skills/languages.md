# languages

Prompts come in 7 languages. Map terms to Tripletex API fields regardless of language.

## Languages
- **nb** — Norwegian Bokmål
- **nn** — Norwegian Nynorsk
- **en** — English
- **de** — German
- **fr** — French
- **es** — Spanish
- **pt** — Portuguese

## Key term mappings

### Employee (POST /employee)
| Field | nb | nn | en | de | fr | es | pt |
|-------|----|----|----|----|----|----|-----|
| firstName | fornavn | fornamn | first name | Vorname | prénom | nombre | nome |
| lastName | etternavn | etternamn | last name | Nachname | nom | apellido | sobrenome |
| email | e-post/epost | e-post | email | E-Mail | e-mail/courriel | correo | e-mail/correio |
| phoneNumber | telefon | telefon | phone | Telefon | téléphone | teléfono | telefone |
| department | avdeling | avdeling | department | Abteilung | département | departamento | departamento |
| administrator | kontoadministrator | kontoadministrator | account administrator | Kontoadministrator | administrateur | administrador | administrador |

### Customer (POST /customer)
| Field | nb | nn | en | de | fr | es | pt |
|-------|----|----|----|----|----|----|-----|
| name | navn/firmanavn | namn | name | Name/Firmenname | nom | nombre | nome |
| email | e-post | e-post | email | E-Mail | e-mail | correo | e-mail |
| phoneNumber | telefon | telefon | phone | Telefon | téléphone | teléfono | telefone |
| organizationNumber | organisasjonsnummer/orgnr | organisasjonsnummer | org. number | Organisationsnummer | numéro d'organisation | número de organización | número da organização |
| isCustomer | kunde | kunde | customer | Kunde | client | cliente | cliente |
| isSupplier | leverandør | leverandør | supplier | Lieferant | fournisseur | proveedor | fornecedor |

### Product (POST /product)
| Field | nb | nn | en | de | fr | es | pt |
|-------|----|----|----|----|----|----|-----|
| name | navn/produktnavn | namn | name | Name | nom | nombre | nome |
| number | produktnummer/nummer | produktnummer | product number | Produktnummer | numéro de produit | número de producto | número do produto |
| priceExcludingVat | pris uten mva/pris eks. mva | pris utan mva | price excl. VAT | Preis ohne MwSt | prix HT | precio sin IVA | preço sem IVA |
| priceIncludingVat | pris med mva/pris inkl. mva | pris med mva | price incl. VAT | Preis inkl. MwSt | prix TTC | precio con IVA | preço com IVA |

### Department (POST /department)
| Field | nb | nn | en | de | fr | es | pt |
|-------|----|----|----|----|----|----|-----|
| name | avdelingsnavn/navn | avdelingsnamn | name | Name | nom | nombre | nome |
| departmentNumber | avdelingsnummer | avdelingsnummer | department number | Abteilungsnummer | numéro de département | número de departamento | número do departamento |

### Invoice (POST /invoice)
| Field | nb | nn | en | de | fr | es | pt |
|-------|----|----|----|----|----|----|-----|
| invoiceDate | fakturadato | fakturadato | invoice date | Rechnungsdatum | date de facture | fecha de factura | data da fatura |
| invoiceDueDate | forfallsdato | forfallsdato | due date | Fälligkeitsdatum | date d'échéance | fecha de vencimiento | data de vencimento |
| customer | kunde | kunde | customer | Kunde | client | cliente | cliente |
| payment | betaling | betaling | payment | Zahlung | paiement | pago | pagamento |
| credit note | kreditnota | kreditnota | credit note | Gutschrift | avoir | nota de crédito | nota de crédito |

### Project (POST /project)
| Field | nb | nn | en | de | fr | es | pt |
|-------|----|----|----|----|----|----|-----|
| name | prosjektnavn | prosjektnamn | project name | Projektname | nom du projet | nombre del proyecto | nome do projeto |
| number | prosjektnummer | prosjektnummer | project number | Projektnummer | numéro de projet | número de proyecto | número do projeto |
| projectManager | prosjektleder | prosjektleiar | project manager | Projektleiter | chef de projet | jefe de proyecto | gerente de projeto |

### Travel Expense (POST /travelExpense)
| Field | nb | nn | en | de | fr | es | pt |
|-------|----|----|----|----|----|----|-----|
| title | tittel/reise | tittel/reise | title/trip | Titel/Reise | titre/voyage | título/viaje | título/viagem |
| departureDate | avreisedato | avreisedato | departure date | Abreisedatum | date de départ | fecha de salida | data de partida |
| returnDate | returdato | returdato | return date | Rückkehrdatum | date de retour | fecha de regreso | data de retorno |
| employee | ansatt | tilsett | employee | Mitarbeiter | employé | empleado | empregado |

### Common action words
| Action | nb | nn | en | de | fr | es | pt |
|--------|----|----|----|----|----|----|-----|
| create | opprett/lag | opprett/lag | create | erstellen | créer | crear | criar |
| update | oppdater/endre | oppdater/endre | update/modify | aktualisieren/ändern | mettre à jour/modifier | actualizar/modificar | atualizar/modificar |
| delete | slett/fjern | slett/fjern | delete/remove | löschen/entfernen | supprimer | eliminar/borrar | excluir/remover |
| register | registrer | registrer | register | registrieren | enregistrer | registrar | registrar |
| search | søk/finn | søk/finn | search/find | suchen/finden | chercher/trouver | buscar/encontrar | procurar/encontrar |
| assign | tildel | tildel | assign | zuweisen | attribuer | asignar | atribuir |
| set as | sett som | sett som | set as | setzen als | définir comme | establecer como | definir como |

### Roles & permissions
| Role | nb | nn | en | de | fr | es | pt |
|------|----|----|----|----|----|----|-----|
| account administrator | kontoadministrator | kontoadministrator | account administrator | Kontoadministrator | administrateur du compte | administrador de cuenta | administrador da conta |
| project manager | prosjektleder | prosjektleiar | project manager | Projektleiter | chef de projet | jefe de proyecto | gerente de projeto |
| department manager | avdelingsleder | avdelingsleiar | department manager | Abteilungsleiter | chef de département | jefe de departamento | chefe de departamento |

## Tips
- Names (firstName, lastName) are always passed through as-is — don't translate them
- Email addresses are always passed through as-is
- Numbers (amounts, org numbers, phone numbers) are passed through as-is
- The API always uses English field names regardless of prompt language
- Norwegian uses both "æ", "ø", "å" — pass these as UTF-8
