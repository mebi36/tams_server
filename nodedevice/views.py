from http import HTTPStatus
import json
import os

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application
from django.http import Http404, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from db.models import NodeDevice
from db.datasynch import dump_data, EXCLUDED_TABLES
from nodedevice.serializers import NodeDeviceSerializer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tams_server.settings")
application = get_wsgi_application()


def device_fixtures(request):
    """Get data to be used to populate new device db."""
    data = dump_data()
    return JsonResponse(json.dumps(data), safe=False)


class NodeDeviceDetail(APIView):
    """Retrieve, update or delete a node_device instance."""

    def get_object(self, pk):
        try:
            return NodeDevice.objects.get(pk=pk)
        except NodeDevice.DoesNotExist:
            return Http404

    def get(self, request, pk, format=None):
        node_device = self.get_object(pk)
        serializer = NodeDeviceSerializer(node_device)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        node_device = self.get_object(pk)
        serializer = NodeDeviceSerializer(node_device, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        node_device = self.get_object(pk)
        node_device.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NodeDeviceList(APIView):
    """List all node devices, or create a new node_device."""

    def get(self, request, format=None):
        node_devices = NodeDevice.objects.all()
        serializer = NodeDeviceSerializer(node_devices, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = NodeDeviceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NodeSyncView(APIView):
    def get(self, request, device_id, token):
        dump_file = os.path.join('dumps', 'server_dump.json')
        try:
            node_device = NodeDevice.objects.get(id=device_id)
        except NodeDevice.DoesNotExist:
            return HttpResponseBadRequest("Node device does not exist")
        
        if node_device.token != token:
            return HttpResponseForbidden("Node Device Authentication Failed")

        # dump the data in a file
        output = open(dump_file, 'w')  # Point stdout at a file for dumping data to.
        call_command('dumpdata', 'db', exclude=EXCLUDED_TABLES, format='json', stdout=output)
        output.close()

        output = open(dump_file)  # reading the dumped data
        response_data = json.load(output)
        output.close()

        # cleaning up temp_files for security and space conservation
        os.remove(dump_file)
        return Response(response_data)

