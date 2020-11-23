from django.contrib import admin
from .models import Account, Task, Participation, ParsedFile, MappingInfo, SchemaAttribute, MappingPair, OriginFile


admin.site.register(Account)
admin.site.register(Task)
admin.site.register(Participation)
admin.site.register(ParsedFile)
admin.site.register(MappingInfo)
admin.site.register(OriginFile)
admin.site.register(SchemaAttribute)
admin.site.register(MappingPair)
