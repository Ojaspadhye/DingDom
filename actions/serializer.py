from rest_framework import serializers
from rest_framework.exceptions import ValidationError

class CreateActionSerializer(serializers.Serializer):
    STATUS = (
        100, 101, 102, 103,
        200, 201, 202, 203, 204, 205, 206, 207, 208, 226,
        300, 301, 302, 303, 304, 305, 306, 307, 308,
        400, 401, 402, 403, 404, 405, 506, 407, 408, 409, 410,
        411, 412, 413, 414,415, 416, 417, 418, 422, 423, 424, 425, 426, 428, 429, 431, 451,
        500, 501, 502, 503, 504, 505, 506, 507, 508, 510, 511
    )

    urls = serializers.URLField()
    name = serializers.CharField(max_length=50)
    frequency = serializers.IntegerField()
    expected_status = serializers.IntegerField()
    is_active = serializers.BooleanField()

    def validate(self, attrs):
        freq = attrs.get("frequency")
        status = attrs.get("expected_status")

        if not freq:
            return ValidationError("Frequency not provided")
        
        if freq > 50:
            raise ValidationError("Frequency too high")
        
        if not status or status not in self.STATUS:
            raise ValidationError("Expected Status is incorrect")
        
        return attrs