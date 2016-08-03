import os
from uuid import uuid4
import hashlib
import json
import urllib2

from flask import Flask, jsonify, request, json, send_from_directory, redirect
import cloudinary
import cloudinary.api
import cloudinary.uploader

from memegenerator import make_meme

import config


app = Flask(__name__)
cloudinary.config(**config.CLOUDINARY_CONF)


def encode_id(name):
    hash = hashlib.sha256(config.SERVER_SECRET)
    hash.update(name)
    public_id_hash = hash.hexdigest()[0:config.HASH_LENGTH]
    public_id = "-".join([name, public_id_hash])
    return public_id


def decode_id(public_id):
    return public_id.rsplit("-", 1)[0]


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in config.ALLOWED_EXTENSIONS


def list_source_images():
    images_all_data = cloudinary.api.resources(
        type="upload",
        prefix=config.SOURCE_IMAGES_PATH
    )
    resources = images_all_data["resources"]

    def formatResource(resource):
        base_string = "http://res.cloudinary.com/polirytmi/image/upload"
        quality = "q_60"
        image_id = "{id}.{format}".format(
            id=resource["public_id"],
            format=resource["format"]
        )
        thumbnail_url = "{base}/{quality}/{image_id}".format(
            base=base_string,
            quality=quality,
            image_id=image_id
        )
        name = resource["public_id"].split("/")[-1]
        return {"title": decode_id(name), "thumb_url": thumbnail_url}
    return map(formatResource, resources)


def create_meme(name, top_text, bottom_text):
    source_images = list_source_images()
    source_image_names = map(lambda i: i.get("title"), source_images)
    # Check that such an image exists, respond with error if not
    if name not in source_image_names:
        image_not_found_text = "The image [{name}] was not found." \
            " Here's a list of valid images:".format(name=name)
        response = {
            "text": image_not_found_text,
            "attachments": source_images
        }
        return jsonify(response), 200

    # Find correct download url
    source_image = source_images[source_image_names.index(name)]
    image_url = source_image["thumb_url"]

    # Make meme to local file
    filename = make_meme(top_text, bottom_text, image_url)

    # Upload meme to Cloudinary
    upload = cloudinary.uploader.upload(
        "images/{filename}".format(filename=filename)
    )

    # Respond with downloadable url
    response = {
        "response_type": "in_channel",
        "attachments": [{
            "image_url": upload['secure_url'],
            "text": "Here you go"
        }]
    }
    return json.dumps(response)


def send_message(url, content):
    req = urllib2.Request(url)
    req.add_header('Content-Type', 'application/json')
    response = urllib2.urlopen(req, content)
    return response


@app.route('/add', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':

        # check if the post request has the file part
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        filename = file.filename
        public_name = request.form.get("public_id")
        if not public_name:
            # TODO: return error
            return redirect(request.url)
        # if user does not select file, browser also
        # submit a empty part without filename
        if filename == '':
            return redirect(request.url)
        if file and allowed_file(filename):
            filetype = filename.rsplit('.', 1)[1]
            filename_tmp = "{uuid}.{ext}".format(
                uuid=str(uuid4()),
                ext=filetype
            )
            filepath = os.path.join(config.UPLOAD_FOLDER, filename_tmp)
            public_id = encode_id(public_name)

            file.save(filepath)
            cloudinary.uploader.upload(
                filepath,
                folder=config.SOURCE_IMAGES_PATH,
                public_id=public_id
            )
            # TODO: show success
            return redirect(request.url)
    return '''
    <!doctype html>
    <title>Lataa uusi kuva</title>
    <h1>Lataa uusi kuva</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p>
         <label for=public_id>Nimi:</label>
         <input type=text name=public_id>
         <label for=file>Kuva:</label>
         <input type=file name=file>
         <input type=submit value=Lataa>
    </form>
    '''


@app.route('/monitor')
def monitor():
    return 'OK', 200


@app.route('/', methods=['POST'])
def main():
    text_not_found_response = jsonify({
        "text": 'Missing required parameter "text"'
    })
    help_response = jsonify({
        "text": "TODO: usage instructions"
    })

    response_url = request.form.get("response_url")
    text = request.form.get("text")
    # Message needs to be as parameter "text"
    if not text:
        return text_not_found_response, 400

    args = text.split(" ", 1)
    name = args[0]
    if len(args) == 1:
        content = None
    else:
        content = args[1]

    if name == "help":
        return help_response, 200
    elif name == "pics":
        return "TODO: list pics", 200
    elif not content:
        return help_response, 200

    if len(content.split("/")) == 1:
        top_text = ""
        bottom_text = content
    else:
        [top_text, bottom_text] = content.split("/", 1)

    message = create_meme(name, top_text.strip(), bottom_text.strip())
    send_message(response_url, message)
    return jsonify({"text": "homma ok"}), 200
