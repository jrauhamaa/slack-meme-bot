from flask import Flask, jsonify, request, json, send_from_directory
from memegenerator import make_meme
import cloudinary
import cloudinary.uploader
import cloudinary.api

cloudinary.config(
  cloud_name = "polirytmi",
  api_key = "457765985322576",
  api_secret = "JX4FiBiLVx5GdRVTGPXqU-RxiYI"
)

app = Flask(__name__)

SOURCE_IMAGES_PATH = "source_images"
image_dict = {
    "doge": "doge.jpg"
}

@app.route('/monitor')
def monitor():
    return 'OK', 200

@app.route('/', methods=['POST'])
def hello_world():
    data = json.loads(request.data)
    # TODO: support the actual slack request format
    message = data.get("message")
    if not message:
        return '', 400
    # Message format is expected to be "[name] [top text]/[bottom text]" or "[name] [bottom text]"
    try:
        [name, content] = message.split(" ", 1)
    except ValueError:
        return '', 400  # TODO: return instructions on how to use the bot
    source_image_name = image_dict.get(name)
    if not source_image_name:
        return '', 400  # TODO: tell the user that the image wasn't found

    image_path = "{path}/{name}".format(path=SOURCE_IMAGES_PATH, name=source_image_name)
    if len(content.split("/")) == 1:
        top_text = ""
        bottom_text = content
    else:
        [top_text, bottom_text] = content.split("/", 1)
    bottom_text = bottom_text.strip()
    top_text = top_text.strip()

    filename = make_meme(top_text, bottom_text, image_path)
    file_url = "{url_root}images/{filename}".format(url_root=request.url_root, filename=filename)

    upload = cloudinary.uploader.upload("images/{filename}".format(filename=filename))
    meme_url = upload['secure_url']

    response = {
        "response_type": "in_channel",
        "text": meme_url
    }
    return jsonify(response)


@app.route('/images/<filename>')
def send_image(filename):
    return send_from_directory('images', filename)
