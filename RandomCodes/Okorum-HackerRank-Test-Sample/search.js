const API = require("./mock-api");
// To count the matches, call API.countMatches(term) where term is the search term
const EventEmitter = require("events");

class Search extends EventEmitter {
  searchCount(searchTerm) {
    // 1. Handle invalid input (undefined)
    if (searchTerm === undefined) {
      this.emit("SEARCH_ERROR", {
        message: "INVALID_TERM",
      });
      return; // Stop execution immediately
    }

    // 2. Emit start event
    this.emit("SEARCH_STARTED", searchTerm);

    // 3. Call the async API
    API.countMatches(searchTerm)
      .then((count) => {
        // 4. Handle successful promise resolution
        this.emit("SEARCH_SUCCESS", {
          count: count,
          term: searchTerm,
        });
      })
      .catch((error) => {
        // 5. Handle promise rejection (API error)
        this.emit("SEARCH_ERROR", {
          message: error.message,
          term: searchTerm,
        });
      });
  }
}

module.exports = Search;
