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

@app.route('/monitor')
def monitor():
    return 'OK', 200

def list_source_images():
    images_all_data = cloudinary.api.resources(type = "upload", prefix = SOURCE_IMAGES_PATH)
    resources = images_all_data["resources"]
    def formatResource(resource):
        base_string = "http://res.cloudinary.com/polirytmi/image/upload"
        quality = "q_60"
        image_id = "{id}.{format}".format(id = resource["public_id"], format = resource["format"])
        thumbnail_url = "{base}/{quality}/{image_id}".format(base = base_string, quality = quality, image_id = image_id)
        name = resource["public_id"].split("/")[-1]
        return {"title": name, "thumb_url": thumbnail_url}
    return map(formatResource, resources)

def create_meme(name, top_text, bottom_text):
    source_images = list_source_images()
    source_image_names = map(lambda i: i.get("title"), source_images)
    #Check that such an image exists, respond with error if not
    if name not in source_image_names:
        #formatted_urls = map(lambda i: "<{}|{}>".format(i["image_url"], i["title"]), source_images)
        #response_text = "\n".join(formatted_urls)
        image_not_found_text = "The image {name} was not found. Here's a list of valid images:".format(name = name)
        response = {
            "text": image_not_found_text,
            "attachments": source_images
        }
        return jsonify(response), 200
    #Find correct download url
    source_image = source_images[source_image_names.index(name)]
    image_url = source_image["thumb_url"]

    #Make meme to local file
    filename = make_meme(top_text, bottom_text, image_url)

    #Upload meme to Cloudinary
    upload = cloudinary.uploader.upload("images/{filename}".format(filename=filename))

    #Respond with downloadable url
    meme_url = "<{url}|Check this out!>".format(url = upload['secure_url'])
    response = {
        "response_type": "in_channel",
        "text": meme_url
    }
    return jsonify(response), 200

@app.route('/', methods=['POST'])
def main():
    text_not_found_response = jsonify({
        "text": 'Missing required parameter "text"'
    })
    help_response = jsonify({
        "text": "TODO: usage instructions"
    })

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
    else:
        if len(content.split("/")) == 1:
            top_text = ""
            bottom_text = content
        else:
            [top_text, bottom_text] = content.split("/", 1)
        return create_meme(name, top_text.strip(), bottom_text.strip())
