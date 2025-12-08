const Search = require("./search");

const search = new Search();

search.on("SEARCH_STARTED", (term) => {
  console.log("Search started for term :", term);
});

search.on("SEARCH_ERROR", (result) => {
  console.log(`Error in search for term "${result.term}"`, result.message);
});

search.on("SEARCH_SUCCESS", (result) => {
  console.log(`Search Completed for term "${result.term}"`, result.count);
});

search.searchCount("error");
search.searchCount();
search.searchCount("test");
