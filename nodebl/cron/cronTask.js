
const cron = require('node-cron');
const configs = require('../configs');

// daos
const taskDAO = require('../daos/task');
const settingDAO = require('../daos/setting');

const constants = require('../constants');
const utils = require('../libs/utils');
const predictionContract = require('../libs/smartcontract');
const network_id = configs.network_id;
const ownerAddress = configs.network[network_id].ownerAddress;

const web3 = require('../configs/web3').getWeb3();
let isRunningTask = false;


const submitMultiTnx = (arr) => {
	return new Promise((resolve, reject) => {
		predictionContract.getNonce(ownerAddress, 'pending')
		.then(nonce => {
			let tasks = [];
			let index = 0;
			arr.forEach((item) => {
				let smartContractFunc = null;
				const onchainData = item.onchainData;
				switch (onchainData.contract_method) {
					case 'init':
						smartContractFunc = predictionContract.submitInitTransaction(nonce + index, onchainData.hid, onchainData.side, onchainData.odds, onchainData.offchain, onchainData.value, item);
					break;
					case 'collectTestDrive':
						smartContractFunc = predictionContract.submitCollectTestDriveTransaction(onchainData.hid, onchainData.winner, onchainData.offchain, nonce + index, item);
					break;
					case 'reportOutcomeTransaction':
						smartContractFunc = predictionContract.reportOutcomeTransaction(onchainData.hid, onchainData.outcome_result, nonce + index, item);
					break;
					case 'initTestDriveTransaction':
						smartContractFunc = predictionContract.submitInitTestDriveTransaction(onchainData.hid, onchainData.side, onchainData.odds, onchainData.maker, onchainData.offchain, parseFloat(onchainData.amount), nonce + index, item);
					break;
					case 'shakeTestDriveTransaction':
						smartContractFunc = predictionContract.submitShakeTestDriveTransaction(onchainData.hid, onchainData.side, onchainData.taker, onchainData.takerOdds, onchainData.maker, onchainData.makerOdds, onchainData.offchain, parseFloat(onchainData.amount), nonce + index, item);
					break;
				}
				index += 1;
				tasks.push(smartContractFunc);
			});
			Promise.all(tasks)
			.then(result => {
				// TODO UPDATTE STATUS TASK
				return resolve();
			})
			.catch(err => {
				return reject(err);
			})
		})
		.catch(err => {
			return reject(err);
		})
	});
}


const init = (params) => {
	return new Promise((resolve, reject) => {
		if (offchain.indexOf('_m') != -1) {
			return resolve(Object.assign({
				contract_method: 'initTestDriveTransaction'
			}, params));
		} else {
			return resolve(Object.assign({
				contract_method: 'shakeTestDriveTransaction',
				maker: params.maker_address,
				makerOdds: parseInt(params.maker_odds * 100)
			}, params));
		}
	});
};


const unInit = (params) => {
	return new Promise((resolve, reject) => {

	});
};

/**
 * 
 * @param {number} params.type
 * @param {JSON string} params.extra_data
 * @param {number} params.outcome_id
 * @param {number} params.odds
 * @param {number} params.amount
 * @param {string} params.currency
 * @param {number} params.side
 * @param {string} params.from_address
 */
const initDefault = (params) => {
	return new Promise((resolve, reject) => {
		utils.submitInitAPI(params)
		.then(result => {
			return resolve(Object.assign(result, {
				contract_method: 'init'
			}))
		})
		.catch(err => {
			//TODO: handle error
			return reject(err);
		})
	});
};

/**
 * @param {number} params.hid
 * @param {number} outcome_result
 */
const report = (params) => {
	return new Promise((resolve, reject) => {
		return resolve({
			contract_method: 'reportOutcomeTransaction',
			hid: params.hid,
			outcome_result: params.outcome_result
		})
	});
};

/**
 * @param {number} params.hid
 * @param {string} params.winner
 * @param {string} params.offchain
 */
const collect = (params) => {
	return new Promise((resolve, reject) => {
		return resolve({
			contract_method: 'collectTestDrive',
			hid: params.hid,
			winner: params.winner,
			offchain: params.offchain
		})
	});
};

/**
 * @param {number} params.market_fee
 * @param {string} params.source
 * @param {string} params.offchain
 */

const createMarket = (params) => {
	return new Promise((resolve, reject) => {
		console.log('DTHTRONG ->', params);

	});
}

const asyncScanTask = () => {
	return new Promise((resolve, reject) => {
		const tasks = [];
		taskDAO.getTasksByStatus()
		.then(_tasks => {
			_tasks.forEach(task => {
				if (task && task.task_type && task.data) {
					tasks.push(
						new Promise((resolve, reject) => {
							taskDAO.updateStatusById(task, constants.TASK_STATUS.STATUS_PROGRESSING)
							.then( resultUpdate => {
								const params = JSON.parse(task.data)
								let processTaskFunc = undefined;
			
								switch (task.task_type) {
									case 'REAL_BET':
										switch (task.action) {
											case 'INIT_DEFAULT':
												processTaskFunc = initDefault(params);
											break;
											case 'REPORT':
												processTaskFunc = report(params);
											break;
											case 'CREATE_MARKET':
												processTaskFunc = createMarket(params);
											break;
										}
									break;

									case 'FREE_BET':
										switch (task.action) {
											case 'INIT':
												processTaskFunc = init(params);
											break;
											case 'UNINIT':
												processTaskFunc = unInit(params);
											break;
											case 'COLLECT':
												processTaskFunc = collect(params);
											break;
										}
									break;
								}

								if (!processTaskFunc) {
									return reject({
										err_type: `TASK_TYPE_NOT_FOUND`,
										options_data: {
											task: task.toJSON()
										}
									});
								}
			
								processTaskFunc
								.then(result => {
									return resolve({
										onchainData: result,
										task: task.toJSON()
									});
								})
								.catch(err => {
									return reject(err);
								});
							})
							.catch(err => {
								return reject({
									err_type: `UPDATE_TASK_STATUS_FAIL`,
									error: err,
									options_data: {
										task: task.toJSON()
									}
								});
							})
						})
					);
				} else {
					console.error('Task is empty with id: ', task.id);
				}
			});

			Promise.all(tasks)
			.then(results => {
				console.log('START SUBMIT MULTI TRANSACTION!');
				submitMultiTnx(results)
				.then(tnxResults => {
					console.log('SUBMIT MULTI TNX DONE WITH RESULT: ');
					console.log(tnxResults);
				})
				.catch(err => {
					console.error('Error', err);
				})
			})
			.catch(err => {
				console.error('Error', err);
			})
		});
	})
};

const runTaskCron = () => {
    cron.schedule('*/5 * * * * *', async () => {
		console.log('task cron running a task every 5s at ' + new Date());
		try {
			const setting = await settingDAO.getByName('TaskCronJob');
				if (!setting) {
					console.log('TaskCronJob setting is null. Exit!');
					return;
				}
				if(!setting.status) {
					console.log('Exit TaskCronJob setting with status: ' + setting.status);
					return;
				}
				console.log('Begin run TaskCronJob!');

			if (isRunningTask === false) {
				isRunningTask = true;
				
				asyncScanTask()
				.then(results => {
					console.log('EXIT SCAN TASK: ', result);
					isRunningTask = false;
				})
				.catch(e => {
					throw e;
				})

			} else {
        console.log('CRON JOB SCAN TASK IS RUNNING!');
			}
		} catch (e) {
			isRunningTask = false;
			console.log('cron task error');
			console.error(e);
		}
	});
};

module.exports = { runTaskCron };
