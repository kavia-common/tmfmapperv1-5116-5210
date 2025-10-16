from flask_smorest import Blueprint
from flask.views import MethodView
from flask import current_app, jsonify
from app.services.catalogue import CatalogueService

blp = Blueprint("Catalogue", "catalogue", url_prefix="/tmf", description="TMF Resource Catalogue")

# PUBLIC_INTERFACE
@blp.route("/catalogue", methods=["GET"])
class Catalogue(MethodView):
    """
    Returns a TMF-style resource catalogue derived from the currently loaded native OpenAPI schema.
    The output includes resource name, description, key attributes, all attributes with types/required flags,
    and inferred CRUD capabilities when determinable from the OpenAPI paths.
    """
    def get(self):
        app = current_app
        service = CatalogueService(app.schema_loader)
        catalogue = service.generate_catalogue()
        return jsonify({"catalogue": catalogue, "generatedFromSchema": service.schema_info()})
