from flask_smorest import Blueprint
from flask.views import MethodView
from flask import current_app, jsonify
from app.services.catalogue import CatalogueService

blp = Blueprint("Catalogue", "catalogue", url_prefix="/tmf", description="TMF Resource Catalogue")

# PUBLIC_INTERFACE
@blp.route("/catalogue", methods=["GET"])
class Catalogue(MethodView):
    """
    Returns a simplified TMF-like resource catalogue derived from the native schema.
    """
    def get(self):
        app = current_app
        service = CatalogueService(app.schema_loader)
        catalogue = service.generate_catalogue()
        return jsonify({"catalogue": catalogue, "generatedFromSchema": service.schema_info()})
