from django.contrib import admin
from .models import Account, Task, Participation, ParsedFile, MappingInfo, SchemaAttribute, MappingPair


admin.site.register(Account)
admin.site.register(Task)
admin.site.register(Participation)
admin.site.register(MappingInfo)
admin.site.register(SchemaAttribute)
admin.site.register(MappingPair)
admin.site.register(ParsedFile)

