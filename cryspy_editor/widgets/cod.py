import urllib.request
import urllib.parse
import re


def load_cif_from_cod_by_formula(formula: str) -> str:
    """Load the first CIF file from COD database by chemical formula.

    Args:
        formula (str): Chemical formula in Hill notation.

    Returns:
        str: CIF file content.
    """

    # Search URL
    search_url = "https://qiserver.ugr.es/cod/result.php"
    data = urllib.parse.urlencode({'formula': formula}).encode('utf-8')
    req = urllib.request.Request(search_url, data=data)
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
    except Exception as e:
        raise ValueError(f"Failed to search COD for formula {formula}: {e}")

    # Parse HTML for COD IDs

    cod_ids = re.findall(r'\"(\d+)\.cif\"', html)
    if not cod_ids:
        raise ValueError(f"No CIF files found for formula {formula}.")

    # Take the first COD ID
    cod_id = cod_ids[0]

    # Download the CIF
    url = f"https://www.crystallography.net/cod/{cod_id}.cif"
    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        raise ValueError(f"Failed to load CIF file from COD with id {cod_id}: {e}")
    
# print(load_cif_from_cod_by_formula('Al'))
