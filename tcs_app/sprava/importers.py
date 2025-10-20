# sprava/importers.py

import csv
import re
import pandas as pd
from io import TextIOWrapper
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.utils import timezone
from contacts.models import Kontakt, Vratka

# =============================================================================
# POMOCNÉ FUNKCE (BEZE ZMĚNY)
# =============================================================================

def _norm_phone(s: str) -> str:
    if not s: return ""
    return re.sub(r"[^\d+]", "", str(s).strip())

def _norm_text(s: str) -> str:
    return str(s).strip() if pd.notna(s) else ""

def _fix_chars(text):
    if not isinstance(text, str):
        return text
    char_map = {
        'Å': 'Č', 'å': 'č', '²': 'ď', 'Þ': 'Ř', 'þ': 'ř', '¯': 'Š', 'æ': 'š',
        'ù': 'ť', '}': 'ü', 'è': 'ů', '½': 'Ž', '¶': 'ž', '\xa0': 'ě',
        '»': 'ň', '¦': 'ö',
    }
    for wrong, correct in char_map.items():
        text = text.replace(wrong, correct)
    return text

# =============================================================================
# LOGIKA PRO IMPORT KONTAKTŮ (CSV)
# =============================================================================

def import_contacts_from_csv(csv_file):
    try:
        decoded_file = TextIOWrapper(csv_file, encoding="utf-8", errors='replace')
        reader = csv.DictReader(decoded_file)
        rows = list(reader)
    except (csv.Error, Exception) as e:
        return {"success": False, "message": f"Chyba při čtení CSV souboru: {e}"}

    created_count = 0
    updated_count = 0
    skipped_duplicates = 0
    
    all_info_2 = {_norm_text(r.get("info_2")) for r in rows if r.get("info_2")}
    all_telefon1 = {_norm_phone(r.get("Telefon1")) for r in rows if r.get("Telefon1")}

    existing_by_info_2 = {k.info_2: k for k in Kontakt.objects.filter(info_2__in=all_info_2)}
    existing_by_telefon1 = {k.telefon1: k for k in Kontakt.objects.filter(telefon1__in=all_telefon1)}
    
    contacts_to_create = []
    contacts_to_update = []
    seen_keys = set()

    with transaction.atomic():
        for raw_row in rows:
            row = {k: _fix_chars(v) for k, v in raw_row.items()}
            telefon1 = _norm_phone(row.get("Telefon1"))
            info_2 = _norm_text(row.get("info_2"))
            key = (telefon1, info_2)
            
            if not any(key) or key in seen_keys:
                if any(key): skipped_duplicates += 1
                continue
            seen_keys.add(key)

            existing_kontakt = existing_by_info_2.get(info_2) if info_2 else existing_by_telefon1.get(telefon1)

            if existing_kontakt:
                new_info3 = _norm_text(row.get("info_3"))
                if existing_kontakt.info_3 != new_info3:
                    existing_kontakt.info_3 = new_info3
                    contacts_to_update.append(existing_kontakt)
            else:
                datum_str = _norm_text(row.get("Geburtsdatum"))
                geburtsdatum = None
                if datum_str:
                    try: geburtsdatum = datetime.strptime(datum_str, "%d-%m-%Y").date()
                    except (ValueError, TypeError): pass
                
                # --- ZMĚNA 1: Přehlednější vytvoření instance ---
                data = {
                    'info_2': info_2, 'info_3': _norm_text(row.get("info_3")),
                    'ansprache': _norm_text(row.get("Ansprache")), 'titel': _norm_text(row.get("Titel")),
                    'vorname': _norm_text(row.get("Vorname")), 'nachname': _norm_text(row.get("Nachname")),
                    'dlbs': _norm_text(row.get("dlbs")), 'info_1': _norm_text(row.get("info_1")),
                    'telefon1': telefon1, 'telefon2': _norm_phone(row.get("Telefon2")),
                    'geburtsdatum': geburtsdatum, 'datum_letztkontakt': _norm_text(row.get("Datum Letztkontakt")),
                    'tlm_kampagne_2_zielprodukt': _norm_text(row.get("TLM-Kampagne 2 - Zielprodukt")),
                    'strasse': _norm_text(row.get("Strasse")), 'ort': _norm_text(row.get("Ort")),
                    'plz': _norm_text(row.get("Plz")), 'recency': _norm_text(row.get("Recency")),
                    'vip': False, 'aktivni': True,
                }
                contacts_to_create.append(Kontakt(**data))

        if contacts_to_create:
            created_objs = Kontakt.objects.bulk_create(contacts_to_create, ignore_conflicts=True)
            created_count = len(created_objs)
        
        if contacts_to_update:
            Kontakt.objects.bulk_update(contacts_to_update, fields=['info_3'])
            updated_count = len(contacts_to_update)

    return {"success": True, "total": len(rows), "created": created_count, "updated": updated_count, "skipped": skipped_duplicates}

# =============================================================================
# LOGIKA PRO IMPORT VRATEK (XLSX) - REFAKTOROVÁNO PRO VÝKON
# =============================================================================

def import_vratky_from_excel(excel_file):
    try:
        # 1. Načtení a příprava dat z Excelu
        df = pd.read_excel(excel_file, dtype={'Acct No.': str})
        df.columns = df.columns.str.strip()

        column_map = {
            'Agent No.': 'agent', 'Acct No.': 'customer_id', 'Inv. No.': 'invoice_id', 
            'Inv Date': 'invoice_date', 'Inv Amount': 'invoice_amount', 
            'Return Date': 'return_date', 'Return Type': 'return_type', 
            'Return Amount': 'return_amount'
        }
        df.rename(columns=column_map, inplace=True)

        summary = {"total_rows": len(df), "processed": 0, "updated": 0, "created": 0, "skipped": 0, "errors": 0}
        
        # 2. Předzpracování dat v Pandas (mnohem rychlejší než řádek po řádku)
        df.dropna(subset=['customer_id', 'return_date'], inplace=True)
        summary['skipped'] = summary['total_rows'] - len(df)

        df['return_date'] = pd.to_datetime(df['return_date'], errors='coerce', format='%Y%m%d').dt.date
        df['invoice_date'] = pd.to_datetime(df['invoice_date'], errors='coerce', format='%Y%m%d').dt.date
        
        def to_decimal(x):
            try: return Decimal(str(x).replace(',', '.'))
            except (InvalidOperation, TypeError): return Decimal('0.00')

        df['return_amount'] = df['return_amount'].apply(to_decimal)
        df['invoice_amount'] = df['invoice_amount'].apply(to_decimal)

        # 3. Hromadné operace s databází
        with transaction.atomic():
            customer_ids = df['customer_id'].unique().tolist()
            
            # Najdeme existující kontakty a vytvoříme ty, které chybí
            existing_kontakty = {k.info_2: k for k in Kontakt.objects.filter(info_2__in=customer_ids)}
            
            new_kontakty_to_create = []
            for cid in customer_ids:
                if cid not in existing_kontakty:
                    new_kontakty_to_create.append(Kontakt(info_2=cid, nachname=f'Zákazník {cid}', aktivni=True))
            
            if new_kontakty_to_create:
                Kontakt.objects.bulk_create(new_kontakty_to_create)
                # Znovu načteme, abychom měli všechny (i nově vytvořené)
                existing_kontakty = {k.info_2: k for k in Kontakt.objects.filter(info_2__in=customer_ids)}

            # Připravíme data pro update_or_create
            vratky_to_process = []
            for row in df.itertuples():
                kontakt = existing_kontakty.get(row.customer_id)
                if not kontakt or pd.isna(row.return_date):
                    summary['errors'] += 1
                    continue

                vratka_data = {
                    'kontakt': kontakt,
                    'cislo_faktury': _norm_text(row.invoice_id),
                    'datum_vratky': row.return_date,
                    'defaults': {
                        'duvod': _norm_text(row.return_type),
                        'castka_vratky': row.return_amount,
                        'agent': _norm_text(row.agent),
                        'datum_faktury': row.invoice_date if not pd.isna(row.invoice_date) else None,
                        'castka_faktury': row.invoice_amount,
                        'datum_importu': timezone.now()
                    }
                }
                vratky_to_process.append(vratka_data)

            # Projdeme a provedeme update_or_create (tohle je stále iterativní, ale už s připravenými daty)
            for data in vratky_to_process:
                _, created = Vratka.objects.update_or_create(**data)
                if created:
                    summary['created'] += 1
                else:
                    summary['updated'] += 1
                summary['processed'] += 1

        summary["success"] = True
        return summary

    except Exception as e:
        return {"success": False, "message": f"Nastala kritická chyba při zpracování souboru: {e}. Zkontrolujte formát souboru."}