from flask import Flask, request, jsonify, render_template
from ModeloXGB import PredictByCountry
import ModeloXGB as mxgb
#from flask_cors import CORS

app = Flask(__name__, static_url_path='/static')
#CORS(app)

@app.route('/')
def index():
    return render_template('index.html')
@app.route('/home')
def home():
    return render_template('index.html')
@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')
@app.route('/filesUsed')
def filesUsed():
    return render_template('filesUsed.html')
@app.route('/theProject')
def theProject():
    return render_template('theProject.html')



@app.route('/process', methods=['POST'])


def process():
    yes = ["sí", "si", "correcto", "así es", "asi es", "cierto", "afirmativo", "positivo", "en efecto", "poco", "un poco", "a veces", "siempre", "mucho", "a menudo", "demasiado"]
    data = request.json
    pais = str(data['pais'])
    
    fuma = str(data['fuma']).lower()
    if fuma in yes:
        fuma = 0.97
    else:
        fuma = 1
    result = PredictByCountry(pais) * fuma  # Your processing logic here
    #result = mxgb.test(pais)

    #Redondeamos el resultado a 2 decimales
    result = str(result)[0:4]
    return jsonify({'result': result})

if __name__ == '__main__':
    app.run(debug=True)
