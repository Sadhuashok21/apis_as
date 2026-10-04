"""
SkilTrix SAP ABAP Lab - Synthetic Enterprise Datasets
Provides realistic master data and transactional records for standard SAP tables
used in educational Open SQL queries and SE11/SE16N dictionary exploration.
"""

from typing import Dict, List, Any, Optional

STANDARD_DATASETS: Dict[str, Dict[str, Any]] = {
    "KNA1": {
        "description": "General Customer Master",
        "category": "Master Data",
        "key_fields": ["MANDT", "KUNNR"],
        "columns": [
            {"name": "MANDT", "type": "CLNT", "length": 3, "key": True, "description": "Client"},
            {"name": "KUNNR", "type": "CHAR", "length": 10, "key": True, "description": "Customer Number"},
            {"name": "NAME1", "type": "CHAR", "length": 35, "key": False, "description": "Name 1"},
            {"name": "LAND1", "type": "CHAR", "length": 3, "key": False, "description": "Country Key"},
            {"name": "ORT01", "type": "CHAR", "length": 35, "key": False, "description": "City"},
            {"name": "PSTLZ", "type": "CHAR", "length": 10, "key": False, "description": "Postal Code"},
            {"name": "STRAS", "type": "CHAR", "length": 35, "key": False, "description": "Street and House No."},
            {"name": "TELF1", "type": "CHAR", "length": 16, "key": False, "description": "First Telephone No."},
        ],
        "rows": [
            {
                "MANDT": "100",
                "KUNNR": "0000001000",
                "NAME1": "Walmart Global Procurement",
                "LAND1": "US",
                "ORT01": "Bentonville",
                "PSTLZ": "72716",
                "STRAS": "702 SW 8th St",
                "TELF1": "+1-479-273-4000",
            },
            {
                "MANDT": "100",
                "KUNNR": "0000001001",
                "NAME1": "Siemens AG Industrial Systems",
                "LAND1": "DE",
                "ORT01": "Munich",
                "PSTLZ": "80333",
                "STRAS": "Werner-von-Siemens-Str 1",
                "TELF1": "+49-89-636-00",
            },
            {
                "MANDT": "100",
                "KUNNR": "0000001002",
                "NAME1": "Apple Operations Europe",
                "LAND1": "IE",
                "ORT01": "Cork",
                "PSTLZ": "T23",
                "STRAS": "Hollyhill Industrial Estate",
                "TELF1": "+353-21-428-4000",
            },
            {
                "MANDT": "100",
                "KUNNR": "0000001003",
                "NAME1": "Tata Motors Ltd Global",
                "LAND1": "IN",
                "ORT01": "Mumbai",
                "PSTLZ": "400001",
                "STRAS": "Bombay House 24 Homi Mody St",
                "TELF1": "+91-22-6665-8282",
            },
            {
                "MANDT": "100",
                "KUNNR": "0000001004",
                "NAME1": "Toyota Motor Corporation",
                "LAND1": "JP",
                "ORT01": "Toyota City",
                "PSTLZ": "471-8571",
                "STRAS": "1 Toyota-cho Aichi",
                "TELF1": "+81-565-28-2121",
            },
            {
                "MANDT": "100",
                "KUNNR": "0000001005",
                "NAME1": "Reliance Industries Retail",
                "LAND1": "IN",
                "ORT01": "Navi Mumbai",
                "PSTLZ": "400701",
                "STRAS": "Reliance Corporate Park",
                "TELF1": "+91-22-4477-0000",
            },
        ],
    },
    "VBAK": {
        "description": "Sales Document Header",
        "category": "Transaction Data",
        "key_fields": ["MANDT", "VBELN"],
        "columns": [
            {"name": "MANDT", "type": "CLNT", "length": 3, "key": True, "description": "Client"},
            {"name": "VBELN", "type": "CHAR", "length": 10, "key": True, "description": "Sales Document"},
            {"name": "ERDAT", "type": "DATS", "length": 8, "key": False, "description": "Creation Date"},
            {"name": "ERNAM", "type": "CHAR", "length": 12, "key": False, "description": "Created By"},
            {"name": "NETWR", "type": "CURR", "length": 15, "key": False, "description": "Net Value"},
            {"name": "WAERK", "type": "CUKY", "length": 5, "key": False, "description": "Document Currency"},
            {"name": "VKORG", "type": "CHAR", "length": 4, "key": False, "description": "Sales Organization"},
            {"name": "VTWEG", "type": "CHAR", "length": 2, "key": False, "description": "Distribution Channel"},
            {"name": "SPART", "type": "CHAR", "length": 2, "key": False, "description": "Division"},
            {"name": "KUNNR", "type": "CHAR", "length": 10, "key": False, "description": "Sold-to Party"},
        ],
        "rows": [
            {
                "MANDT": "100",
                "VBELN": "0090000001",
                "ERDAT": "20250115",
                "ERNAM": "DEVELOPER",
                "NETWR": 12500.00,
                "WAERK": "USD",
                "VKORG": "1000",
                "VTWEG": "10",
                "SPART": "00",
                "KUNNR": "0000001000",
            },
            {
                "MANDT": "100",
                "VBELN": "0090000002",
                "ERDAT": "20250120",
                "ERNAM": "DEVELOPER",
                "NETWR": 4800.50,
                "WAERK": "EUR",
                "VKORG": "1000",
                "VTWEG": "10",
                "SPART": "00",
                "KUNNR": "0000001001",
            },
            {
                "MANDT": "100",
                "VBELN": "0090000003",
                "ERDAT": "20250201",
                "ERNAM": "DEVELOPER",
                "NETWR": 92000.00,
                "WAERK": "USD",
                "VKORG": "2000",
                "VTWEG": "20",
                "SPART": "01",
                "KUNNR": "0000001000",
            },
            {
                "MANDT": "100",
                "VBELN": "0090000004",
                "ERDAT": "20250210",
                "ERNAM": "SAPUSER",
                "NETWR": 150000.00,
                "WAERK": "INR",
                "VKORG": "3000",
                "VTWEG": "10",
                "SPART": "00",
                "KUNNR": "0000001003",
            },
            {
                "MANDT": "100",
                "VBELN": "0090000005",
                "ERDAT": "20250218",
                "ERNAM": "SAPUSER",
                "NETWR": 31400.00,
                "WAERK": "EUR",
                "VKORG": "1000",
                "VTWEG": "10",
                "SPART": "00",
                "KUNNR": "0000001002",
            },
        ],
    },
    "VBAP": {
        "description": "Sales Document Item",
        "category": "Transaction Data",
        "key_fields": ["MANDT", "VBELN", "POSNR"],
        "columns": [
            {"name": "MANDT", "type": "CLNT", "length": 3, "key": True, "description": "Client"},
            {"name": "VBELN", "type": "CHAR", "length": 10, "key": True, "description": "Sales Document"},
            {"name": "POSNR", "type": "NUMC", "length": 6, "key": True, "description": "Item Number"},
            {"name": "MATNR", "type": "CHAR", "length": 18, "key": False, "description": "Material Number"},
            {"name": "ARKTX", "type": "CHAR", "length": 40, "key": False, "description": "Short Text for Sales Order Item"},
            {"name": "KWMENG", "type": "QUAN", "length": 13, "key": False, "description": "Cumulative Order Quantity"},
            {"name": "VRKME", "type": "UNIT", "length": 3, "key": False, "description": "Sales Unit"},
            {"name": "NETWR", "type": "CURR", "length": 15, "key": False, "description": "Net Value of Item"},
            {"name": "WAERK", "type": "CUKY", "length": 5, "key": False, "description": "Currency"},
        ],
        "rows": [
            {
                "MANDT": "100",
                "VBELN": "0090000001",
                "POSNR": "000010",
                "MATNR": "MAT-100-A",
                "ARKTX": "Industrial Motor 50kW",
                "KWMENG": 5,
                "VRKME": "PC",
                "NETWR": 10000.00,
                "WAERK": "USD",
            },
            {
                "MANDT": "100",
                "VBELN": "0090000001",
                "POSNR": "000020",
                "MATNR": "MAT-200-B",
                "ARKTX": "Control Panel Inverter",
                "KWMENG": 2,
                "VRKME": "PC",
                "NETWR": 2500.00,
                "WAERK": "USD",
            },
            {
                "MANDT": "100",
                "VBELN": "0090000002",
                "POSNR": "000010",
                "MATNR": "MAT-300-C",
                "ARKTX": "Copper Wiring Assembly 100m",
                "KWMENG": 10,
                "VRKME": "PC",
                "NETWR": 4800.50,
                "WAERK": "EUR",
            },
            {
                "MANDT": "100",
                "VBELN": "0090000003",
                "POSNR": "000010",
                "MATNR": "MAT-100-A",
                "ARKTX": "Industrial Motor 50kW",
                "KWMENG": 40,
                "VRKME": "PC",
                "NETWR": 80000.00,
                "WAERK": "USD",
            },
            {
                "MANDT": "100",
                "VBELN": "0090000003",
                "POSNR": "000020",
                "MATNR": "MAT-200-B",
                "ARKTX": "Control Panel Inverter",
                "KWMENG": 10,
                "VRKME": "PC",
                "NETWR": 12000.00,
                "WAERK": "USD",
            },
        ],
    },
    "MARA": {
        "description": "General Material Master",
        "category": "Master Data",
        "key_fields": ["MANDT", "MATNR"],
        "columns": [
            {"name": "MANDT", "type": "CLNT", "length": 3, "key": True, "description": "Client"},
            {"name": "MATNR", "type": "CHAR", "length": 18, "key": True, "description": "Material Number"},
            {"name": "MTART", "type": "CHAR", "length": 4, "key": False, "description": "Material Type"},
            {"name": "MATKL", "type": "CHAR", "length": 9, "key": False, "description": "Material Group"},
            {"name": "MEINS", "type": "UNIT", "length": 3, "key": False, "description": "Base Unit of Measure"},
            {"name": "BRGEW", "type": "QUAN", "length": 13, "key": False, "description": "Gross Weight"},
            {"name": "NTGEW", "type": "QUAN", "length": 13, "key": False, "description": "Net Weight"},
            {"name": "GEWEI", "type": "UNIT", "length": 3, "key": False, "description": "Weight Unit"},
        ],
        "rows": [
            {
                "MANDT": "100",
                "MATNR": "MAT-100-A",
                "MTART": "FERT",
                "MATKL": "ELEC01",
                "MEINS": "PC",
                "BRGEW": 120.50,
                "NTGEW": 115.00,
                "GEWEI": "KG",
            },
            {
                "MANDT": "100",
                "MATNR": "MAT-200-B",
                "MTART": "FERT",
                "MATKL": "ELEC02",
                "MEINS": "PC",
                "BRGEW": 15.20,
                "NTGEW": 14.00,
                "GEWEI": "KG",
            },
            {
                "MANDT": "100",
                "MATNR": "MAT-300-C",
                "MTART": "ROH",
                "MATKL": "RAW01",
                "MEINS": "PC",
                "BRGEW": 45.00,
                "NTGEW": 42.50,
                "GEWEI": "KG",
            },
            {
                "MANDT": "100",
                "MATNR": "MAT-400-D",
                "MTART": "HALB",
                "MATKL": "SEMI01",
                "MEINS": "EA",
                "BRGEW": 3.80,
                "NTGEW": 3.50,
                "GEWEI": "KG",
            },
            {
                "MANDT": "100",
                "MATNR": "MAT-500-E",
                "MTART": "ROH",
                "MATKL": "CHEM01",
                "MEINS": "L",
                "BRGEW": 1.10,
                "NTGEW": 1.00,
                "GEWEI": "KG",
            },
        ],
    },
    "MAKT": {
        "description": "Material Descriptions",
        "category": "Master Data",
        "key_fields": ["MANDT", "MATNR", "SPRAS"],
        "columns": [
            {"name": "MANDT", "type": "CLNT", "length": 3, "key": True, "description": "Client"},
            {"name": "MATNR", "type": "CHAR", "length": 18, "key": True, "description": "Material Number"},
            {"name": "SPRAS", "type": "LANG", "length": 1, "key": True, "description": "Language Key"},
            {"name": "MAKTX", "type": "CHAR", "length": 40, "key": False, "description": "Material Description"},
        ],
        "rows": [
            {"MANDT": "100", "MATNR": "MAT-100-A", "SPRAS": "E", "MAKTX": "Industrial Motor 50kW"},
            {"MANDT": "100", "MATNR": "MAT-200-B", "SPRAS": "E", "MAKTX": "Control Panel Inverter"},
            {"MANDT": "100", "MATNR": "MAT-300-C", "SPRAS": "E", "MAKTX": "Copper Wiring Assembly 100m"},
            {"MANDT": "100", "MATNR": "MAT-400-D", "SPRAS": "E", "MAKTX": "Sub-assembly Gear Housing"},
            {"MANDT": "100", "MATNR": "MAT-500-E", "SPRAS": "E", "MAKTX": "Synthetic Lubricant Oil ISO VG 46"},
        ],
    },
    "LFA1": {
        "description": "Vendor Master Data",
        "category": "Master Data",
        "key_fields": ["MANDT", "LIFNR"],
        "columns": [
            {"name": "MANDT", "type": "CLNT", "length": 3, "key": True, "description": "Client"},
            {"name": "LIFNR", "type": "CHAR", "length": 10, "key": True, "description": "Account Number of Vendor"},
            {"name": "NAME1", "type": "CHAR", "length": 35, "key": False, "description": "Name 1"},
            {"name": "LAND1", "type": "CHAR", "length": 3, "key": False, "description": "Country Key"},
            {"name": "ORT01", "type": "CHAR", "length": 35, "key": False, "description": "City"},
            {"name": "PSTLZ", "type": "CHAR", "length": 10, "key": False, "description": "Postal Code"},
        ],
        "rows": [
            {"MANDT": "100", "LIFNR": "0000005001", "NAME1": "Bosch Rexroth Hydraulics", "LAND1": "DE", "ORT01": "Lohr am Main", "PSTLZ": "97816"},
            {"MANDT": "100", "LIFNR": "0000005002", "NAME1": "ABB Global Power Grids", "LAND1": "CH", "ORT01": "Zurich", "PSTLZ": "8050"},
            {"MANDT": "100", "LIFNR": "0000005003", "NAME1": "Schneider Electric Solutions", "LAND1": "FR", "ORT01": "Rueil-Malmaison", "PSTLZ": "92500"},
            {"MANDT": "100", "LIFNR": "0000005004", "NAME1": "Mitsubishi Electric Factory Auto", "LAND1": "JP", "ORT01": "Tokyo", "PSTLZ": "100-8310"},
        ],
    },
}


SYNTHETIC_CUSTOM_TABLES: Dict[str, Dict[str, Any]] = {}


def register_custom_synthetic_table(
    table_name: str,
    columns: Optional[List[Any]] = None,
    description: str = "Custom Transparent Table",
    rows: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    clean = table_name.strip().upper()
    cols_clean = []
    key_fields = []
    for c in (columns or []):
        if isinstance(c, dict):
            cols_clean.append(c)
            if c.get("key"):
                key_fields.append(c.get("name") or c.get("field"))
        elif isinstance(c, str):
            cols_clean.append({"name": c, "type": "CHAR", "length": 30, "key": False})
    table_dict = {
        "description": description,
        "category": "Custom Application Table",
        "key_fields": key_fields,
        "columns": cols_clean,
        "rows": list(rows or []),
    }
    SYNTHETIC_CUSTOM_TABLES[clean] = table_dict
    return table_dict


def remove_custom_synthetic_table(table_name: str) -> bool:
    clean = table_name.strip().upper()
    if clean in SYNTHETIC_CUSTOM_TABLES:
        del SYNTHETIC_CUSTOM_TABLES[clean]
        return True
    return False


def get_standard_table(table_name: str, user_id: Optional[str] = None, project_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    clean_name = table_name.strip().upper()
    std = STANDARD_DATASETS.get(clean_name)
    if std:
        return std

    # User scoped lookups bypass the process-wide synthetic cache. Custom
    # dictionary rows belong to one user/project and must not bleed between runs.
    if user_id is not None:
        try:
            from ..abap_models import ABAPDictionaryTable
            query = ABAPDictionaryTable.objects.filter(table_name__iexact=clean_name, user_id=user_id)
            custom_tbl = None
            if project_id:
                custom_tbl = query.filter(project__project_id=project_id, project__user_id=user_id).first()
            if not custom_tbl:
                custom_tbl = query.first()
            if not custom_tbl:
                custom_tbl = ABAPDictionaryTable.objects.filter(table_name__iexact=clean_name).first()
            if custom_tbl:
                return {
                    "description": custom_tbl.description,
                    "category": "Custom Application Table",
                    "key_fields": [f.get("field") for f in (custom_tbl.fields_schema or []) if f.get("key")],
                    "columns": [
                        {"name": f.get("field"), "type": f.get("type", "CHAR"),
                         "length": f.get("length", 10), "key": f.get("key", False),
                         "description": f.get("description", "")}
                        for f in (custom_tbl.fields_schema or [])
                    ],
                    "rows": list(custom_tbl.sample_records or []),
                }
        except Exception:
            pass

    if clean_name in SYNTHETIC_CUSTOM_TABLES:
        return SYNTHETIC_CUSTOM_TABLES[clean_name]

    # Check MySQL local database for dynamic SE11 transparent tables created by users
    try:
        from ..abap_models import ABAPDictionaryTable
        custom_tbl = ABAPDictionaryTable.objects.filter(table_name__iexact=clean_name).first()
        if custom_tbl:
            tbl_meta = {
                "description": custom_tbl.description,
                "category": "Custom Application Table",
                "key_fields": [f.get("field") for f in (custom_tbl.fields_schema or []) if f.get("key")],
                "columns": [
                    {
                        "name": f.get("field"),
                        "type": f.get("type", "CHAR"),
                        "length": f.get("length", 10),
                        "key": f.get("key", False),
                        "description": f.get("description", ""),
                    }
                    for f in (custom_tbl.fields_schema or [])
                ],
                "rows": custom_tbl.sample_records or [],
            }
            SYNTHETIC_CUSTOM_TABLES[clean_name] = tbl_meta
            return tbl_meta
    except Exception:
        pass
    return None


def query_synthetic_table(
    table_name: str,
    fields: List[str] = None,
    where_filter: Optional[Any] = None,
    order_by: Optional[str] = None,
    descending: bool = False,
    up_to_rows: Optional[int] = None,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Simulates an Open SQL SELECT query against standard SAP datasets and custom MySQL user tables."""
    dataset = get_standard_table(table_name, user_id=user_id, project_id=project_id)
    if not dataset:
        return []

    rows = list(dataset["rows"])

    # Apply filter if provided
    if where_filter and callable(where_filter):
        rows = [r for r in rows if where_filter(r)]

    # Apply sorting
    if order_by:
        field_clean = order_by.strip().upper()
        rows.sort(
            key=lambda r: r.get(field_clean, 0) if isinstance(r.get(field_clean), (int, float)) else str(r.get(field_clean, "")),
            reverse=descending,
        )

    # Apply row limit
    if up_to_rows is not None and up_to_rows > 0:
        rows = rows[:up_to_rows]

    # Project fields
    if fields and "*" not in fields:
        clean_fields = [f.strip().upper() for f in fields]
        projected = []
        for r in rows:
            projected.append({k: r.get(k) for k in clean_fields if k in r})
        return projected

    return [dict(r) for r in rows]

