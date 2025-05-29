from astropy.io import fits
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from astropy.table import Table
from flask import Flask, render_template, request, send_from_directory, redirect, url_for, flash
import os
import io
import base64
import matplotlib
matplotlib.use('Agg')
from werkzeug.utils import secure_filename
import subprocess

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'fits', 'fit', 'fts'}

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    files = []

    for fname in os.listdir(app.config['UPLOAD_FOLDER']):
        if allowed_file(fname):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
            metadata = {
                "name": fname,
                "date_obs": "N/A",
                "telescope": "N/A",
                "object": "N/A"
            }

            try:
                with fits.open(file_path) as hdul:
                    header = hdul[0].header
                    metadata["date_obs"] = header.get("DATE-OBS", "N/A")
                    metadata["telescope"] = header.get("TELESCOP", "N/A")
            except Exception as e:
                metadata["error"] = f"Kļūda faila nolasīšanā: {e}"

            files.append(metadata)

    return render_template('index.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():

    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))
    file = request.files['file']

    if file.filename == '':
        flash('Nav izvēlēts fails')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash('Augšupielāde veiksmīga!')

    else:
        flash('Neatbalstīts faila tips. Pieņem tikai .fits, .fit vai .fts failus.')
    return redirect(url_for('index'))

@app.route('/view/<filename>')
def view_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    hdu_views = []

    try:
        with fits.open(file_path) as hdul:
            for i, hdu in enumerate(hdul):
                hdu_type = type(hdu).__name__
                name = hdu.name
                shape = hdu.data.shape if hdu.data is not None else None

                hdu_info = {
                    "index": i,
                    "name": name,
                    "type": hdu_type,
                    "shape": shape,
                    "image": None,
                    "table": None
                }

                if hdu.data is not None and (hdu_type in ["PrimaryHDU", "ImageHDU"]):
                    try:
                        data = hdu.data.astype(float)
                        fig, ax = plt.subplots()
                        im = ax.imshow(data, cmap='gray', norm=LogNorm())
                        plt.colorbar(im, ax=ax, label='Intensitāte')
                        ax.set_title(f'HDU {i}: Attēls')
                        buf = io.BytesIO()
                        plt.savefig(buf, format='png', bbox_inches='tight')
                        plt.close(fig)
                        buf.seek(0)
                        encoded = base64.b64encode(buf.read()).decode('utf-8')
                        hdu_info['image'] = encoded
                    except Exception as e:
                        hdu_info['image'] = f"Attēla ģenerēšanas kļūda: {e}"

                elif hdu_type in ["BinTableHDU", "TableHDU"]:
                    try:
                        tbl = Table(hdu.data)
                        hdu_info['table'] = tbl[:5]  # Only preview first 5 rows
                    except Exception as e:
                        hdu_info['table'] = f"Tabulas nolasīšanas kļūda: {e}"

                hdu_views.append(hdu_info)

    except Exception as e:
        flash(f"Kļūda faila apstrādē: {str(e)}")
        return redirect(url_for('index'))

    return render_template('view.html', filename=filename, hdu_views=hdu_views)

@app.route('/launch-ds9/<filename>/<int:hdu_index>')
def launch_ds9(filename, hdu_index):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(file_path):
        flash('Fails neeksistē.')
        return redirect(url_for('index'))
    ds9_path = os.path.join(os.path.dirname(__file__), 'ds9', 'ds9')  # Adjust path to your DS9 executable if needed
    try:
        subprocess.Popen([os.path.join(os.path.dirname(__file__), 'ds9', 'ds9'),  # or just 'ds9' if globally installed
            f"{file_path}[{hdu_index}]"])
    except Exception as e:
        flash(f"Kļūda, palaižot DS9: {str(e)}")
    
    return redirect(url_for('view_file', filename=filename, hdu_index=hdu_index))

@app.route('/table/<filename>/<int:hdu_index>')
def view_table(filename, hdu_index):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if not os.path.exists(file_path):
        return f"Fails '{filename}' nav atrasts.", 404

    try:
        with fits.open(file_path) as hdul:
            hdu = hdul[hdu_index]

            if not isinstance(hdu, (fits.BinTableHDU, fits.TableHDU)):
                return f"HDU {hdu_index} nav tabula.", 400

            from astropy.table import Table
            table = Table(hdu.data)

            return render_template("full_table.html", table=table, filename=filename, index=hdu_index)

    except Exception as e:
        return f"Kļūda tabulas skatīšanā: {e}", 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
