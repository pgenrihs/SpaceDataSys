from astropy.io import fits
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from astropy.table import Table

hdul = fits.open('FOCx38i0101t_c0f.fits')
hdul.info()

for i, hdu in enumerate(hdul):
    print(i, hdu.name, type(hdu).__name__, hdu.data.shape if hdu.data is not None else None)

    if isinstance(hdu, fits.ImageHDU) or (isinstance(hdu, fits.PrimaryHDU) and hdu.data is not None):
        image_data = hdu.data.astype(float)
        plt.imshow(image_data, cmap='gray', norm=LogNorm())
        plt.colorbar(label='Intensity')
        plt.title(f'HDU {i}: Image (log scale)')
        plt.show()

    elif isinstance(hdu, (fits.BinTableHDU, fits.TableHDU)):
        try:
            tbl = Table(hdu.data)
            print(f"HDU {i} - Table preview:")
            print(tbl[:5])  # Show first 5 rows
        except Exception as e:
            print(f"Could not read table from HDU {i}: {e}")