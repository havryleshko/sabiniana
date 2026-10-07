# Engine folders

Alex drops a statement in `inbox/`. `sabiniana.review.save_review` reads that PDF, checks it, writes the fields and the check result into `working/`, and writes the draft into `reports/`. Alex reads every draft against the statement before anything is sent.

`reference/price_table.json` holds cited rates only. It records the UK consumer interchange caps and the Payment Systems Regulator's observed average merchant service charges by annual card-turnover band for December 2015 to December 2018. Fair all-in rates stay empty. Those observed averages are not a fair price.

Customer files in `inbox/`, `working/`, and `reports/` are not committed.
