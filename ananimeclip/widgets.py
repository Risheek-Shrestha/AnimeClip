from django import forms

class CloudinaryVideoWidget(forms.Widget):
    """
    Renders a Cloudinary Upload Widget button.
    On upload, the returned secure_url is written into a hidden text input
    so Django's form submission picks it up normally.
    """

    def __init__(self, cloud_name, upload_preset, attrs=None):
        self.cloud_name = cloud_name
        self.upload_preset = upload_preset
        super().__init__(attrs)

    def render(self, name, value, attrs=None, renderer=None):
        current_value = value or ''
        preview = ''
        if current_value:
            preview = f'''
                <div style="margin-bottom:8px;">
                    <a href="{current_value}" target="_blank"
                       style="color:#4CAF50;">
                        ✓ Video uploaded — click to preview
                    </a>
                </div>
            '''

        html = f'''
            {preview}
            <input type="hidden" name="{name}" id="id_{name}" value="{current_value}">
            <button type="button"
                    id="upload_btn_{name}"
                    style="padding:8px 16px; background:#4CAF50;
                           color:white; border:none; border-radius:4px;
                           cursor:pointer; font-size:14px;">
                {"Replace Video" if current_value else "Upload Video"}
            </button>
            <script
                src="https://upload-widget.cloudinary.com/global/all.js"
                type="text/javascript">
            </script>
            <script type="text/javascript">
                (function() {{
                    var btn = document.getElementById("upload_btn_{name}");
                    var input = document.getElementById("id_{name}");

                    var widget = cloudinary.createUploadWidget(
                        {{
                            cloudName: "{self.cloud_name}",
                            uploadPreset: "{self.upload_preset}",
                            resourceType: "video",
                            sources: ["local", "url"],
                            multiple: false,
                        }},
                        function(error, result) {{
                            if (!error && result.event === "success") {{
                                input.value = result.info.secure_url;
                                btn.textContent = "Replace Video";
                                btn.style.background = "#2196F3";

                                // Show a quick preview link
                                var existing = btn.previousElementSibling;
                                var link = document.createElement("div");
                                link.style.marginBottom = "8px";
                                link.innerHTML = '<a href="' + result.info.secure_url
                                    + '" target="_blank" style="color:#4CAF50;">'
                                    + '✓ Video uploaded — click to preview</a>';
                                btn.parentNode.insertBefore(link, btn);
                            }}
                        }}
                    );

                    btn.addEventListener("click", function() {{
                        widget.open();
                    }});
                }})();
            </script>
        '''
        return html

    class Media:
        js = ('https://upload-widget.cloudinary.com/global/all.js',)