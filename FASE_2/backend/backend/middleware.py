from django.http import HttpResponse
class CORSMiddleware:
    def __init__(self, get_response):
        # print("Optiones Init ***********")
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'OPTIONS':
            # print("Optiones***********")
            response = HttpResponse()
        else:
            # print("Optiones response***********")
            response = self.get_response(request)

        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE"
        response["Access-Control-Allow-Headers"] = "Access-Control-Allow-Origin,Access-Control-Allow-Methods,Access-Control-Allow-Headers, Content-Type, Authorization"

        return response    
    
# from django.utils.deprecation import MiddlewareMixin
# class CORSMiddleware1(MiddlewareMixin):
#     def process_response(self, request, response):
#         response["Access-Control-Allow-Origin"] = "*"
#         response['Access-Control-Allow-Credentials'] = "true"
#         response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE"
#         response["Access-Control-Allow-Headers"] = 'Access-Control-Allow-Headers, Origin, Accept, ' \
#                                                'X-Requested-With, Content-Type, Access-Control-Request-Method,' \
#                                                ' Access-Control-Request-Headers, credentials'
#         return response
