import React from 'react';

namespace types {
  export type Props = {
    sites: string[];
    onChangeSite: (site: string) => void;
    disableSelection: boolean;
  };
}

/**
 * select component
 * @param props
 * @constructor
 */
export const UnicoreSites = (props: types.Props): JSX.Element => {
  /**
   * function to handle the change of selected option - meant to call the handler from props with
   * the new option value as param
   * @param event
   */
  function handleSiteChange(event: React.ChangeEvent<HTMLSelectElement>): void {
    console.log('site change event: ', event.target.value);
    props.onChangeSite(event.target.value);
  }

  return (
    <div className={'pyunicoreSites'}>
      <div>
        <span>SITE:</span>
        <select onChange={handleSiteChange} disabled={props.disableSelection}>
          {props.sites.map(site => (
            <option key={site} id={site} value={site}>
              {site}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};