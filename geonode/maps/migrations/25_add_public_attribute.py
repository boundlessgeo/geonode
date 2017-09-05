#
# Add public attribute to maps
#

from django.db import migrations, models
from django.conf import settings

class Migration(migrations.Migration):
    dependencies = [
        ('maps','24_initial')
    ]

    operations = [
        migrations.AddField(
            model_name='Map',
            name='public',
            field=models.BooleanField(default=False, blank=True, null=True)
        )
    ]
