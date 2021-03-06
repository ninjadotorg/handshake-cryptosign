'use strict';
module.exports = (sequelize, DataTypes) => {
  var Handshake = sequelize.define('Handshake', {
    id: {
      type: DataTypes.INTEGER,
      autoIncrement: true,
      primaryKey: true,
      allowNull: false,
      unique: true,
    },
    date_created: DataTypes.DATE,
    date_modified: DataTypes.DATE,
    deleted: DataTypes.INTEGER,
    hs_type: DataTypes.INTEGER,
    extra_data: DataTypes.TEXT,
    chain_id: DataTypes.INTEGER,
    state: DataTypes.INTEGER,
    description: DataTypes.TEXT,
    status: DataTypes.INTEGER,
    bk_status: DataTypes.INTEGER,
    from_address: DataTypes.STRING,
    odds: DataTypes.DECIMAL(20, 1),
    amount: DataTypes.DECIMAL(36, 18),
    remaining_amount: DataTypes.DECIMAL(36, 18),
    free_bet: DataTypes.INTEGER,
    currency: DataTypes.STRING,
    side: DataTypes.INTEGER,
    user_id: DataTypes.INTEGER,
    outcome_id: DataTypes.INTEGER,
    contract_address: DataTypes.STRING,
    contract_json: DataTypes.STRING,
    modified_user_id: DataTypes.INTEGER,
    created_user_id: DataTypes.INTEGER
  }, {
    tableName: 'handshake',
    timestamps: false,
    underscored: true,
  });

  Handshake.associate = function (models) {
    Handshake.belongsTo(models.Outcome, { 
      foreignKey: 'outcome_id',
      sourceKey: 'id'
    })
  };

  return Handshake;
};
