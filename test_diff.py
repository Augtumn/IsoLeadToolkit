import numpy as np
import V1V2_reference
import geochemistry

def compare():
    # Test values
    pb206 = np.array([16.589, 18.0, 19.0, 17.5])
    pb207 = np.array([15.317, 15.5, 15.7, 15.4])
    pb208 = np.array([36.784, 38.0, 39.0, 37.5])

    print("--- V1V2 Reference ---")
    ref_res = V1V2_reference.calculate_all_parameters(pb206, pb207, pb208)
    print("Delta Alpha:", ref_res['Delta_alpha'])
    print("Delta Beta:", ref_res['Delta_beta'])
    print("Delta Gamma:", ref_res['Delta_gamma'])

    print("\n--- Geochemistry New ---")
    # Ensure engine is in default Geokit mode
    geochemistry.engine.load_preset("V1V2 (Geokit)")
    
    geo_res = geochemistry.calculate_all_parameters(pb206, pb207, pb208)
    print("Delta Alpha:", geo_res['Delta_alpha'])
    print("Delta Beta:", geo_res['Delta_beta'])
    print("Delta Gamma:", geo_res['Delta_gamma'])
    
    print("\n--- Differences ---")
    diff_alpha = np.abs(ref_res['Delta_alpha'] - geo_res['Delta_alpha'])
    diff_beta = np.abs(ref_res['Delta_beta'] - geo_res['Delta_beta'])
    diff_gamma = np.abs(ref_res['Delta_gamma'] - geo_res['Delta_gamma'])
    
    print("Max Diff Alpha:", np.max(diff_alpha))
    print("Max Diff Beta:", np.max(diff_beta))
    print("Max Diff Gamma:", np.max(diff_gamma))

    print("\n--- Ages ---")
    print("tCDT (Ref):", ref_res.get('tCDT (Ma)'))
    # Note: geochemistry main calc returns tCDT based on default T2 usually, unless we check how it handles it.
    # But for Delta calculation it uses t_single_T1 internal variable.
    # Let's see what it returns.
    print("tCDT (Geo):", geo_res['tCDT (Ma)'])

    tCDT_ref = ref_res.get('tCDT (Ma)')
    tCDT_geo = geo_res['tCDT (Ma)']
    print("Diff tCDT:", np.max(np.abs(tCDT_ref - tCDT_geo)))


if __name__ == "__main__":
    compare()
