function(doc){
	if(doc["Service_Provider"]){
	    emit(doc["Service_Provider"], 1);
	}
}