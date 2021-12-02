import React from 'react';
import { render } from 'react-dom';
import App from 'component/app/app';
import InvalidBuild from 'component/app/invalid_build';

import utils from 'utils';

import 'css/main.css';
import 'css/bootstrap.min.css';
import 'css/custom-theme.css';

/**
 * Set env by appending a URL param e.g. `?dev`, `?test`, or `?prod`.
 */
function maybeSetEnvCookies() {
  const url_params = new URLSearchParams(window.location.search);
  const one_hundred_years_in_hours = 8760 * 100;
  if (url_params.has('dev')) {
    utils.setCookie('env', 'dev', one_hundred_years_in_hours);
  } else if (url_params.has('test')) {
    utils.setCookie('env', 'test', one_hundred_years_in_hours);
  } else if (url_params.has('prod')) {
    utils.setCookie('env', 'prod', one_hundred_years_in_hours);
  }
}

maybeSetEnvCookies();

if (process.env.REACT_APP_GOOGLE_API_KEY) {
  render(
    <App
      is_new_session={!utils.hasExistingSession()}
    />,
    document.getElementById('root')
  );
} else {
  render(
    <InvalidBuild />,
    document.getElementById('root')
  );
}
