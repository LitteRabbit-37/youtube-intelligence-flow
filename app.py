from flask import Flask, render_template, request
import requests
import re
import json

app = Flask(__name__)

# Compile a regular expression to validate YouTube URLs.
# This ensures that the provided URL is a valid YouTube video, channel, or user link.
YOUTUBE_REGEX = re.compile(
    r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/(watch\?v=|channel/|user/|@)[\w\-]+'
)

#########################################################################
#                                                                       #
#   ---- LangFlow API endpoint (change with your actual flow ID) ----   #
#                                                                       #
#########################################################################

# LangFlow API endpoint: Update this URL with the actual flow ID endpoint as required.
FLOW_URL = "http://127.0.0.1:7860/api/v1/run/73ce6066-03f9-4ac2-a899-edeeddfa6a75"


@app.route("/", methods=["GET", "POST"])
def index():
    # Handle GET and POST requests. Initialize variables for the result, response_text, and error messages.
    result = None
    response_text = None
    error = None

    if request.method == "POST":
        # Process the POST request: retrieve and validate the YouTube URL from the form data.
        url = request.form.get("youtube_url")

        # Validate the YouTube URL using the compiled regex. Return an error message if invalid.
        if not url or not YOUTUBE_REGEX.match(url):
            error = "❌ Invalid YouTube URL. Please enter a valid video or channel link."
        else:
            # Construct the JSON payload for the LangFlow API request with input and output specifications.
            payload = {
                "input_value": url,
                "output_type": "chat",
                "input_type": "chat"
            }

            try:
                # Execute the POST request to the LangFlow API endpoint and handle potential exceptions.
                res = requests.post(FLOW_URL, json=payload, headers={
                    "Content-Type": "application/json"
                })
                res.raise_for_status()
                print("📥 Raw response:", res.text)

                # Extract raw response text from the API response and look for embedded markdown and JSON segments.
                raw_response_text = res.json(
                )["outputs"][0]["outputs"][0]["results"]["message"]["text"]

                # If a JSON block is included in the response, split the response to separate markdown stats from JSON analysis.
                if "```json" in raw_response_text:
                    parts = raw_response_text.split("```json", 1)
                    raw_stats_text = parts[0].strip()
                    rest = parts[1]
                    end_marker = "```"
                    end_idx = rest.find(end_marker)
                    if end_idx != -1:
                        json_text = rest[:end_idx].strip()
                    else:
                        json_text = rest.strip()
                else:
                    raw_stats_text = raw_response_text.strip()
                    json_text = ""

                # Process markdown table to create a dictionary of statistics.
                # Only extract headers and corresponding data row if available.
                stats_data = None
                if raw_stats_text:
                    lines = raw_stats_text.splitlines()
                    if len(lines) >= 3:
                        header_line = lines[0]
                        data_line = lines[2]
                        headers = [h.strip()
                                   for h in header_line.split("|") if h.strip()]
                        values = [v.strip()
                                  for v in data_line.split("|") if v.strip()]
                        stats_data = dict(zip(headers, values))
                if stats_data:
                    # Clean and transform the statistics data:
                    # - Remove unwanted keys.
                    # - Rename keys for clarity (e.g., channel_profile_pic, channel_banner).
                    # - Generate a default video thumbnail if not provided.
                    unwanted_keys = ["custom_url", "id"]
                    for key in unwanted_keys:
                        stats_data.pop(key, None)

                    if 'thumbnail_default' in stats_data:
                        stats_data['channel_profile_pic'] = stats_data.pop(
                            'thumbnail_default')
                    if 'brand_banner_url' in stats_data:
                        stats_data['channel_banner'] = stats_data.pop(
                            'brand_banner_url')

                    if 'video_thumbnail' not in stats_data:
                        video_match = re.search(
                            r"(?:v=|youtu\.be/)([\w\-]+)", url)
                        if video_match:
                            video_id = video_match.group(1)
                            stats_data[
                                'video_thumbnail'] = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

                    # Filter the statistics to include only the essential information.
                    allowed_keys = ["title", "view_count",
                                    "subscriber_count", "video_count"]
                    filtered_stats = {}
                    for key in allowed_keys:
                        if key in stats_data:
                            filtered_stats[key] = stats_data[key]

                    if "video_thumbnail" in stats_data:
                        filtered_stats["video_thumbnail"] = stats_data["video_thumbnail"]
                    if "channel_banner" in stats_data:
                        filtered_stats["channel_banner"] = stats_data["channel_banner"]
                    if "channel_profile_pic" in stats_data:
                        filtered_stats["channel_profile_pic"] = stats_data["channel_profile_pic"]

                    stats_data = filtered_stats

                # If a JSON analysis block exists, parse it and integrate additional analysis details.
                # Differentiate between channel and video analysis based on the presence of specific keys.
                if json_text:
                    analysis_json = json.loads(json_text)
                    result = {}
                    if "channel_statistics" in analysis_json:
                        # Process channel analysis: integrate stats and additional recommendations.
                        result["stats"] = stats_data
                        analysis = {}
                        analysis["Content Themes"] = analysis_json.get(
                            "content_themes", "")
                        analysis["Audience Reception"] = analysis_json.get(
                            "audience_reception", "")
                        analysis["Synthesis"] = analysis_json.get(
                            "synthesis", "")
                        recommendations = analysis_json.get(
                            "recommendations", [])
                        rec_html = "<ul style='margin:0; padding:0; list-style:none;'>" + "".join(
                            [f"<li style='margin-bottom:10px;'>{rec}</li>" for rec in recommendations]
                        ) + "</ul>"
                        analysis["Recommendations"] = rec_html
                        result["analysis"] = analysis
                    else:
                        # Process video analysis: integrate stats and additional video-specific analysis details.
                        result["stats"] = stats_data
                        analysis = {}
                        analysis["Content Summary"] = analysis_json.get(
                            "content_summary", "")
                        analysis["Audience Reception"] = analysis_json.get(
                            "audience_reception", "")
                        analysis["Synthesis"] = analysis_json.get(
                            "synthesis", "")
                        recommendations = analysis_json.get(
                            "recommendations", [])
                        rec_html = "<ul style='margin:0; padding:0; list-style:none;'>" + "".join(
                            [f"<li style='margin-bottom:10px;'>{rec}</li>" for rec in recommendations]
                        ) + "</ul>"
                        analysis["Recommendations"] = rec_html
                        result["analysis"] = analysis
                    response_text = None
                else:
                    # If no JSON block exists, rely solely on the extracted markdown statistics.
                    result = {"stats": stats_data, "analysis": {}}
            except Exception as e:
                # Catch and report any errors that occur during the API call or processing.
                error = f"🔥 Error calling LangFlow API: {str(e)}"

    # Render the index.html template with the processed results and any error messages.
    return render_template("index.html", result=result, error=error)


# Initialize and run the Flask application in debug mode for development purposes.
if __name__ == "__main__":
    app.run(debug=True)
