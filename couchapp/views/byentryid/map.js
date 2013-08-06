function(doc){
	if(typeof doc["EntryId"] === 'number')
	    emit(doc.EntryId, 1);
}