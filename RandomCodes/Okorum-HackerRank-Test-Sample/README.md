# Event Emitter: Async Search

## Class Definition
Create a module, search.js, and implement the following set of functionalities:

- The file should export a class Search as the default export of the module, and it should inherit from the EventEmitter class.

### Events:

- Methods
  - searchCount - Argument, term. 
    
    Accepts the searchTerm [STRING] as the argument, and it internally makes use of the predefined API service in order to fetch the count of the matches.
      - If the searchTerm passed to the function is undefined, the function should emit the event `SEARCH_ERROR` with an object containing the message property `INVALID_TERM`, and then immediately return without executing further.
    ```
    {message: 'INVALID_TERM', term : searchTerm}
    // search term is the term passed to the searchCount function
    ```
    
- Emits
  - `SEARCH_STARTED` - Emitted immediately when searchCount function is called. The searchTerm should be passed to the callback function of the event handler.
  
  - `SEARCH_SUCCESS` - Emitted if the countMatches method resolved with a result successfully. The callback function of the event handler should accept an object with the following properties:
      ```
      {count: count, term : searchTerm}
      // Where count is the result returned by the countMatches API
      ```
  - `SEARCH_ERROR` - Emitted if the searchTerm passed to the searchCount function is undefined or the countMatches method rejects with an error.
  The callback function of the event handler should accept an object with the following properties:
    ```
    {message: error message, term : searchTerm}
    // search term is the term passed to the searchCount function
    ```
---   
_NOTE: The API service file, mock-api.js, is present in the root folder of the project and has a single method, countMatches, that accepts searchTerm as input and returns a Promise. The Promise either resolves with a counted number of the matches, or it rejects with a JavaScript Error object. To test rejection for this method, you can pass searchTerm 'error' to the countMatches function._

### Example Implementation

Please open the file `index.js` for example implementation.

## Project Specifications

**Read-Only Paths**
- test

**Commands**
- run: `npm start`
- install: `npm install`
- test: `npm test`
