# Todo bot

## FEATURES SUPPORTED: 
* Add a new task
* Mark a task as finished
* Delete tasks 
* List all tasks to do 
* List all complete tasks 
* Basic NLP for flexible queries (support for usage of multiple verbs, and much more flexible query format)
* Searching for todo items
* Clear all todos (User can select if they want to delete all completed items, all incomplete items, or all elements)
* Displays a tutorial for new users (existing users can access this by typing 'help')
* Allows the user to edit a todo item

## UNIT TESTS
Note: I have never written unit tests before. I have also never deployed a webservice or written script to run on
the web / a server, therefore I am unsure of the tests to perform. Regarding the queries however, this is what I would 
test it against 

* list 
* list all complete
* $1 delete
* $5 done 
* add Eat cookies 
* list 
* list all complete 
* add Finish code 
* add Submit repo 
* list 
* list all complete 
* $2 finish
* $4 finish
* $1 delete
* list 
* list all complete
* add Buy milk 
* add Buy cookies
* add Drink water 
* search cookies 
* search milk 
* search water 
* clear all
* list 
* list all complete
* add Cookies 
* add Bananas
* $1 edit Cake 
* $2 finish
* clear completed
* list 
* list all complete
* help

